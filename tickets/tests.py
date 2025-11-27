from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from .models import User, Ticket, DevReport


class TicketAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # create 3 users: tester / dev / qa
        self.tester = User.objects.create_user(
            username="tester1",
            password="password123",
            role="TESTER",
        )
        self.dev = User.objects.create_user(
            username="dev1",
            password="password123",
            role="DEVELOPER",
        )
        self.qa = User.objects.create_user(
            username="qa1",
            password="password123",
            role="QA",
        )

    def test_tester_can_create_ticket_via_api(self):
        """
        tester call /api/tickets/ to create ticket，examine submitter / assignee and status
        """
        self.client.force_authenticate(user=self.tester)

        data = {
            "title": "Login captcha not shown",
            "description": "On iOS Safari the captcha image is missing.",
            "severity": "CRITICAL",
            "software_name": "Portal",
            "software_version": "1.0.0",
            "module": "Login",
            "discovered_at": timezone.now().isoformat(),
            "assignee": str(self.dev.id),
        }

        resp = self.client.post("/api/tickets/", data, format="json")

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Ticket.objects.count(), 1)

        ticket = Ticket.objects.first()
        self.assertEqual(ticket.submitter, self.tester)
        self.assertEqual(ticket.assignee, self.dev)
        self.assertEqual(ticket.current_status, "OPEN")

    def test_only_assigned_developer_can_submit_dev_report(self):
        """
        test dev-report:
        - The assigned developer(dev1) can send report
        - qa will get 403 if sent
        """
        # create a ticket，assignee to dev1
        ticket = Ticket.objects.create(
            title="Sample bug",
            description="Bug details",
            software_name="Portal",
            software_version="1.0.0",
            discovered_at=timezone.now(),
            severity="NORMAL",
            module="Login",
            submitter=self.tester,
            assignee=self.dev,
            current_status="OPEN",
        )

        dev_payload = {
            "issue_type": "Bug",
            "root_cause": "Null pointer dereference",
            "self_test_report": "Tested on Chrome and Edge.",
            "regression_version": "1.0.1",
            "module": "Login",
            "github_pr_url": "https://example.com/pr/123",
        }

        # 1.normal process
        self.client.force_authenticate(user=self.dev)
        resp_ok = self.client.post(
            f"/api/tickets/{ticket.id}/dev-report/",
            dev_payload,
            format="json",
        )
        self.assertEqual(resp_ok.status_code, status.HTTP_200_OK)
        self.assertEqual(DevReport.objects.filter(ticket=ticket).count(), 1)

        ticket.refresh_from_db()
        self.assertEqual(ticket.current_status, "UNDER_REVIEW")
        dev_report = DevReport.objects.get(ticket=ticket)
        self.assertEqual(dev_report.assigned_developer, self.dev)

        # 2. qa send a request
        self.client.force_authenticate(user=self.qa)
        resp_forbidden = self.client.post(
            f"/api/tickets/{ticket.id}/dev-report/",
            dev_payload,
            format="json",
        )
        self.assertEqual(resp_forbidden.status_code, status.HTTP_403_FORBIDDEN)
