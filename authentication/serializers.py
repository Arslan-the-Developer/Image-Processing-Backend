from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import User



class UserRegistrationSerializer(serializers.ModelSerializer):

    password2 = serializers.CharField(write_only=True)  # Explicitly define password2

    class Meta:

        model = User

        fields = ['username','email','password','password2']


    def validate(self, attrs):

        # FOR THE VALIDATION OF EMAIL PROVIDERS | UNCOMMENT THIS WHEN NEEDED

        # valid_mails_list = ["gmail.com","outlook.com","aol.com","protonmail.com","zoho.com","gmx.com","icloud.com","yahoo.com","mail2world.com","tutanota.com","juno.com"]

        # if attrs['email'] not in valid_mails_list:

        #     raise ValidationError(detail="Disposable Emails Are Not Allowed")
        
        if len(attrs['password']) < 8:

            raise ValidationError(detail="Password Must Have 8 Characters")
        
        if attrs['password'] != attrs['password2']:

            raise ValidationError(detail="Passwords Must Match")
        
        return attrs
    
    def create(self, validated_data):
        
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email']
        )

        user.set_password(validated_data['password'])

        user.save()
        
        return user
