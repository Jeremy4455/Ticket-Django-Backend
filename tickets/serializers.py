from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User, Ticket, QAReview


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
        # 返回与前端一致的结构：仅一个 token + user 对象
        user_data = UserOutSerializer(self.user).data
        return {
            'token': data['access'],
            'user': user_data
        }


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


# --- Users ---
class UserOutSerializer(serializers.ModelSerializer):
    fullName = serializers.CharField(source='full_name', required=False, allow_null=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'fullName', 'email', 'role']


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


# --- Tickets ---
class UserIdOrNestedField(serializers.PrimaryKeyRelatedField):
    def to_internal_value(self, data):
        # 支持 {id: "..."} 或 "..."（UUID字符串）
        if isinstance(data, dict):
            data = data.get('id')
        return super().to_internal_value(data)


class TicketSerializer(serializers.ModelSerializer):
    submitter = UserOutSerializer(read_only=True)
    assignee = UserOutSerializer(read_only=True)
    qa_reviewer = UserOutSerializer(read_only=True)
    regressor = UserOutSerializer(read_only=True)
    qa_reviews = serializers.SerializerMethodField(read_only=True)

    def get_qa_reviews(self, obj):
        qs = obj.qa_reviews.order_by('-created_at')
        return QAReviewOutSerializer(qs, many=True).data

    class Meta:
        model = Ticket
        fields = [
            'id', 'title', 'description',
            'software_name', 'software_version', 'discovered_at',
            'severity', 'module', 'current_status',
            'submitter', 'assignee', 'qa_reviewer', 'regressor', 'qa_reviews',
            'created_at', 'updated_at'
        ]


class TicketCreateSerializer(serializers.ModelSerializer):
    assignee = UserIdOrNestedField(queryset=User.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Ticket
        fields = [
            'title', 'description',
            'software_name', 'software_version', 'discovered_at',
            'severity', 'module', 'assignee'
        ]

    def create(self, validated_data):
        request = self.context.get('request')
        submitter = request.user if request and request.user.is_authenticated else None
        # 若未提供 discovered_at，则使用当前时间
        if 'discovered_at' not in validated_data or validated_data['discovered_at'] is None:
            from django.utils import timezone
            validated_data['discovered_at'] = timezone.now()
        ticket = Ticket.objects.create(
            current_status='OPEN',
            submitter=submitter,
            **validated_data
        )
        return ticket


class DevReportSerializer(serializers.Serializer):
    report = serializers.JSONField(required=False)


class QAReviewSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True)
    agree_to_release = serializers.BooleanField()
    designated_tester = UserIdOrNestedField(queryset=User.objects.all(), required=False, allow_null=True)


class RegressionSerializer(serializers.Serializer):
    passed = serializers.BooleanField()


class QAReviewOutSerializer(serializers.ModelSerializer):
    reviewer = UserOutSerializer(source='release_qa', read_only=True)
    designatedTester = UserOutSerializer(source='designated_tester', read_only=True)

    class Meta:
        model = QAReview
        fields = ['id', 'comment', 'agree_to_release', 'reviewer', 'designatedTester', 'created_at']
