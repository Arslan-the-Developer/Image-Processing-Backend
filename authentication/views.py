from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from rest_framework_simplejwt.tokens import RefreshToken, AccessToken

from .serializers import UserRegistrationSerializer

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.contrib.auth import authenticate

from premailer import transform

import random, string, secrets
from datetime import datetime, timedelta, timezone as dt_timezone
from threading import Thread

from .models import User, OTPVerifyAttempt, LoginAttempt




# -----------------------------------------------------------------------------


class CheckUserAuthentication(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        return Response("Authenticated",status=status.HTTP_200_OK)



# -----------------------------------------------------------------------------



class GetUserDetails(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        return Response({"username" : request.user.username, "email" : request.user.email, "is_seller" : request.user.is_seller, "is_manager" : request.user.is_staff_member ,"is_admin" : request.user.is_admin, "is_protected" : request.user.is_two_factor_authentication_enabled})




class UserRegistrationView(APIView):

    def post(self, request):

        serializer = UserRegistrationSerializer(data=request.data)

        if serializer.is_valid():

            user = serializer.save()

            assign_otp(user=user)

            assign_verification_token(user=user)

            email_thread = Thread(target=send_stylized_email,args=(user.email, "Verify Your Account", "otp.html", {'username': user.username, 'otp':user.otp}))

            email_thread.start()

            return Response({'verification_token':user.verification_token},status=status.HTTP_201_CREATED)
        
    
        else:

            first_error_field = next(iter(serializer.errors))  # Get the first key from the errors dictionary

            first_error_message = f"{serializer.errors[first_error_field][0]}"  # Get the first error message for that field

            return Response({'error':first_error_message},status=status.HTTP_400_BAD_REQUEST)





class VerifyUserOTP(APIView):


    def track_verify_attempt(self, request, user=None, success=False):

        ip_address = get_client_ip(request=request)

        # Delete the Succeccful LoginAttempt of the IP Adress if ever before

        OTPVerifyAttempt.objects.filter(ip_address=ip_address, success=True).delete()
        
        # Create a new Failed LoginAttempt of the IP Address

        OTPVerifyAttempt.objects.create(user=user, ip_address=ip_address, success=success)

    
    def delete_attempts_before_threshold(self, ip_address, duration_minutes):

        time_threshold = timezone.now() - timedelta(minutes=duration_minutes)

        # Delete the Older Failed Login Attempts becuase they are no more revelant

        OTPVerifyAttempt.objects.filter(ip_address=ip_address, success=False, timestamp__lte=time_threshold).delete()

    
    def too_many_attempts(self, request, duration_minutes=15, max_attempts=5):
        
        ip_address = get_client_ip(request)

        time_threshold = timezone.now() - timedelta(minutes=duration_minutes)

        delete_old_attempts_thred = Thread(target=self.delete_attempts_before_threshold,args=(ip_address,duration_minutes))

        delete_old_attempts_thred.start()

        # Count failed login attempts for the IP in the given duration
        failed_attempts = OTPVerifyAttempt.objects.filter(ip_address=ip_address, success=False, timestamp__gte=time_threshold).count()

        return failed_attempts >= max_attempts


    def post(self, request):

        if self.too_many_attempts(request=request):

            return Response({"error":"Too many Verification Requests. Try Again Later"},status=status.HTTP_429_TOO_MANY_REQUESTS)

        incoming_verification_token = request.data.get("verification_token",None)
        incoming_otp = request.data.get("otp",None)

        if incoming_verification_token is not None:

            try:

                user = User.objects.get(verification_token=incoming_verification_token)

                if user.verification_token_expiry is not None and user.verification_token_expiry > timezone.now():

                    if user.otp_expiry is not None and user.otp_expiry > timezone.now() and user.otp == incoming_otp:

                        self.track_verify_attempt(request=request, user=user, success=True)

                        user.is_active = True
                        user.otp = None
                        user.otp_expiry = None
                        user.verification_token = None
                        user.verification_token_expiry = None
            
                        clear_failed_attempts_thread = Thread(target=clean_failed_attempts,args=(request, "otp-attempt"))

                        clear_failed_attempts_thread.start()

                        user.save()

                        tokens = generate_user_tokens(user=user)

                        response = Response({"msg":"OTP Verified, User is Now Active", "store_date" : datetime.now().strftime("%Y-%m-%d"), "store_time" : str(datetime.now().strftime("%H:%M:%S"))},status=status.HTTP_200_OK)

                        return set_tokens_and_expiry(response_object=response, tokens=tokens)
                    
                    else:

                        self.track_verify_attempt(request=request, success=False)

                        return Response({"error":"Invalid or Expired OTP"},status=status.HTTP_400_BAD_REQUEST)
                    
                else:

                    self.track_verify_attempt(request=request, success=False)

                    return Response({"error":"Invalid or Expired Token"}, status=status.HTTP_400_BAD_REQUEST)


            
            except User.DoesNotExist:
                
                self.track_verify_attempt(request=request, success=False)

                return Response({"error":"Invalid or Expired Token"},status=status.HTTP_404_NOT_FOUND)

        


class UserLoginView(APIView):


    
    def track_login_attempt(self, request, user=None, success=False):

        ip_address = get_client_ip(request=request)

        # Delete the Succeccful LoginAttempt of the IP Adress if ever before

        LoginAttempt.objects.filter(ip_address=ip_address, success=True).delete()
        
        # Create a new Failed LoginAttempt of the IP Address

        LoginAttempt.objects.create(user=user, ip_address=ip_address, success=success)

    
    def delete_attempts_before_threshold(self, ip_address, duration_minutes):

        time_threshold = timezone.now() - timedelta(seconds=duration_minutes)

        # Delete the Older Failed Login Attempts becuase they are no more revelant

        LoginAttempt.objects.filter(ip_address=ip_address, success=False, timestamp__lte=time_threshold).delete()

    
    def too_many_attempts(self, request, duration_minutes=15, max_attempts=5):
        
        ip_address = get_client_ip(request)

        time_threshold = timezone.now() - timedelta(seconds=duration_minutes)

        delete_old_attempts_thred = Thread(target=self.delete_attempts_before_threshold,args=(ip_address,duration_minutes))

        delete_old_attempts_thred.start()

        # Count failed login attempts for the IP in the given duration
        failed_attempts = LoginAttempt.objects.filter(ip_address=ip_address, success=False, timestamp__gte=time_threshold).count()

        return failed_attempts >= max_attempts
    

    def post(self, request):

        if self.too_many_attempts(request=request):

            return Response({"error":"Too many Login Requests. Try Again Later"},status=status.HTTP_429_TOO_MANY_REQUESTS)

        email = request.data.get("email")
        password = request.data.get("password")

        user = authenticate(username=email,password=password)

        if user is not None:

            self.track_login_attempt(request=request, user=user, success=True)

            if user.is_two_factor_authentication_enabled:

                return Response({"is_restricted_account" : user.is_two_factor_authentication_enabled, "email" : user.email})
            
            else:

                tokens = generate_user_tokens(user=user)

                clear_failed_attempts_thread = Thread(target=clean_failed_attempts,args=(request, "login-attempt"))

                clear_failed_attempts_thread.start()

                response = Response({"msg":"Login Successful", "store_date" : datetime.now().strftime("%Y-%m-%d"), "store_time" : str(datetime.now().strftime("%H:%M:%S"))},status=status.HTTP_200_OK)

                return set_tokens_and_expiry(response_object=response, tokens=tokens)

            # return Response({"msg":"Login Successful", "access":tokens['access'], "refresh":tokens['refresh'], "store_date" : str(datetime.now().date()), "store_time" : str(datetime.now().time())})
        
        else:
            
            self.track_login_attempt(request=request, success=False)

            return Response({"error":"Invalid Credentials"}, status=status.HTTP_400_BAD_REQUEST)










def send_stylized_email(user_email : str , subject : str, template_name : str , arguments_for_template : dict):
    
    subject = subject

    message = "Email Failed To Send"

    # Render and transform the HTML email
    html_message = render_to_string(template_name, arguments_for_template)
    html_message = transform(html_message)  # Inline CSS

    email = EmailMessage(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [user_email]
    )
    
    email.content_subtype = 'html'
    email.body = html_message

    email.send()



def assign_otp(user : User):

    """
    Assigns User A Unique OTP
    """

    while True:

        generated_otp = "".join(random.choices(population=string.digits,k=4))

        try:

            with transaction.atomic():

                user.otp = generated_otp

                user.otp_expiry = timezone.now() + timedelta(minutes=5)

                user.save()

                break

        except IntegrityError:

            continue



def assign_verification_token(user : User):

    """
    Assigns User A Unique Verification Token
    """

    while True:

        generated_token = secrets.token_urlsafe(32)

        try:

            with transaction.atomic():

                user.verification_token = generated_token

                user.verification_token_expiry = timezone.now() + timedelta(minutes=5)

                user.save()

                return generated_token
            

        except IntegrityError:

            continue


def get_client_ip(request):
    
    """
    Extracts and Returns The IP Address of Request
    """

    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    if x_forwarded_for:

        ip = x_forwarded_for.split(",")[0]

    else:

        ip = request.META.get("REMOTE_ADDR")

    return ip



def clean_failed_attempts(request, attempt_type : str):

    """
    Clears All The Failed Attempts
    """

    client_ip = get_client_ip(request=request)

    match attempt_type :

        case "login-attempt":

            LoginAttempt.objects.filter(ip_address = client_ip, success = False).delete()

            return True
        
        case "otp-attempt":

            OTPVerifyAttempt.objects.filter(ip_address = client_ip, success = False).delete()

            return True
        
        case _:

            return False



def generate_user_tokens(user : User) -> dict:

    """
    Generates and Returns The Access and Refresh Tokens for The User using SimpleJWT
    """

    tokens = RefreshToken.for_user(user)

    return {
        'refresh' : str(tokens),
        'access' : str(tokens.access_token),
    }



def set_tokens_and_expiry(response_object, tokens : dict):

    """
    Set Tokens in The Cookies of Browser and Returns a Response Object
    """

    refresh_token_expiry = datetime.now(dt_timezone.utc) + timedelta(days=5)
    access_token_expiry = datetime.now(dt_timezone.utc) + timedelta(minutes=10)

    response_object.set_cookie('refresh', tokens['refresh'], expires=refresh_token_expiry, secure=True, httponly=True, samesite='None')
    response_object.set_cookie('access', tokens['access'], expires=access_token_expiry, secure=True, httponly=True, samesite='None')

    return response_object