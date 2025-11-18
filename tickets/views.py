from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import User, Ticket, QAReview, DevReport, RegressionTest
from .serializers import (
    UserSerializer,
    UserOutSerializer,
    TicketSerializer,
    TicketCreateSerializer,
    DevReportSerializer,
    QAReviewSerializer,
    RegressionSerializer,
)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.request.method in ['GET']:
            return UserOutSerializer
        return UserSerializer

    permission_classes = [IsAuthenticated]


class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.select_related('submitter', 'assignee', 'qa_reviewer', 'regressor').prefetch_related('qa_reviews', 'dev_reports').all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['create']:
            return TicketCreateSerializer
        return TicketSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = serializer.save()
        out = TicketSerializer(ticket)
        headers = self.get_success_headers(out.data)
        return Response(out.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=['post'], url_path='dev-report')
    def dev_report(self, request, pk=None):
        ticket = self.get_object()
        # 角色校验：仅开发
        if request.user.role != 'DEVELOPER':
            return Response({'detail': 'Only developers can submit dev report.'}, status=403)
        # 通常要求是被指派人
        if ticket.assignee_id and ticket.assignee_id != request.user.id:
            return Response({'detail': 'Only assignee developer can operate.'}, status=403)

        payload = DevReportSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        # 持久化 DevReport 记录
        DevReport.objects.create(
            ticket=ticket,
            assigned_developer=request.user,
            **data,
        )

        ticket.current_status = 'UNDER_REVIEW'
        ticket.save(update_fields=['current_status', 'updated_at'])
        return Response(TicketSerializer(ticket).data)

    @action(detail=True, methods=['post'], url_path='qa-review')
    def qa_review(self, request, pk=None):
        ticket = self.get_object()
        # 角色校验：仅 QA
        if request.user.role != 'QA':
            return Response({'detail': 'Only QA can submit review.'}, status=403)

        payload = QAReviewSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        agree = payload.validated_data['agree_to_release']
        designated = payload.validated_data.get('designated_tester')
        comment = payload.validated_data.get('comment', '')

        # 持久化 QAReview 记录
        QAReview.objects.create(
            ticket=ticket,
            release_qa=request.user,
            agree_to_release=agree,
            designated_tester=designated,
            comment=comment,
        )

        ticket.qa_reviewer = request.user
        if agree:
            ticket.current_status = 'IN_REGRESSION'
            ticket.regressor = designated or ticket.submitter
        else:
            ticket.current_status = 'IN_MODIFICATION'
        ticket.save(update_fields=['qa_reviewer', 'current_status', 'regressor', 'updated_at'])
        return Response(TicketSerializer(ticket).data)

    @action(detail=True, methods=['post'], url_path='regression')
    def regression(self, request, pk=None):
        ticket = self.get_object()
        # 角色校验：仅测试
        if request.user.role != 'TESTER':
            return Response({'detail': 'Only testers can submit regression.'}, status=403)
        # 通常要求为指定的回归测试者
        if ticket.regressor_id and ticket.regressor_id != request.user.id:
            return Response({'detail': 'Only designated tester can operate.'}, status=403)

        payload = RegressionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        RegressionTest.objects.create(
            ticket=ticket,
            tester=request.user,
            regression_version=payload.validated_data.get('regression_version', ''),
            passed=payload.validated_data['passed'],
            report=payload.validated_data.get('report', '')
        )

        payload = RegressionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        if payload.validated_data['passed']:
            ticket.current_status = 'CLOSED'
        else:
            ticket.current_status = 'UNDER_REVIEW'
        ticket.save(update_fields=['current_status', 'updated_at'])
        return Response(TicketSerializer(ticket).data)
