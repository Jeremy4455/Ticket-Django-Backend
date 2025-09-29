from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # 在 token 中添加自定义字段
        token['username'] = user.username
        token['role'] = user.role
        return token

    def validate(self, attrs):
        # 支持 email 或 username 登录
        credentials = {
            'username': '',
            'password': attrs.get('password')
        }

        # 检查输入是 email 还是 username
        user_input = attrs.get('username')
        if '@' in user_input:
            try:
                user = User.objects.get(email=user_input)
                credentials['username'] = user.username
            except User.DoesNotExist:
                raise serializers.ValidationError('Invalid email or password')
        else:
            credentials['username'] = user_input

        data = super().validate(credentials)
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'email', 'role', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            email=validated_data.get('email'),
            full_name=validated_data.get('full_name'),
            role=validated_data.get('role', 'TESTER')
        )
        return user