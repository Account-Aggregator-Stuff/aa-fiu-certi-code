from rest_framework import serializers
from .models import ConsentStatusNotification, FIStatusNotification, Account, FIStatusResponse

class ConsentStatusNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsentStatusNotification
        fields = ['ver', 'timestamp', 'txnid']

from rest_framework import serializers

class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['link_ref_number', 'fi_status', 'description']

class FIStatusResponseSerializer(serializers.ModelSerializer):
    accounts = AccountSerializer(many=True)

    class Meta:
        model = FIStatusResponse
        fields = ['fipID', 'accounts']

class FIStatusNotificationSerializer(serializers.ModelSerializer):
    fi_responses = FIStatusResponseSerializer(many=True)

    class Meta:
        model = FIStatusNotification
        fields = ['ver', 'timestamp', 'txnid', 'notifier_type', 'notifier_id', 'session_id', 'session_status', 'fi_responses']
    
    def create(self, validated_data):
        fi_responses_data = validated_data.pop('fi_responses')
        fi_notification = FIStatusNotification.objects.create(**validated_data)
        for fi_response_data in fi_responses_data:
            accounts_data = fi_response_data.pop('accounts')
            fi_response = FIStatusResponse.objects.create(fi_notification=fi_notification, **fi_response_data)
            for account_data in accounts_data:
                Account.objects.create(fi_status_response=fi_response, **account_data)
        return fi_notification
