from django.db import models
import uuid

from django.forms import model_to_dict


class SoftDeletionQuerySet(models.QuerySet):
    def active(self):
        return self.filter(deleted_at=None)

    def deleted(self):
        return self.exclude(deleted_at=None)


class SoftDeletionModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeletionQuerySet.as_manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = models.DateTimeField(auto_now=True)
        self.save()

    def undelete(self):
        self.deleted_at = None
        self.save()


class ConsentStatusNotification(SoftDeletionModel):
    class Meta:
        db_table = "consent_status_notifications"

    ver = models.CharField(max_length=10)
    timestamp = models.DateTimeField()
    txnid = models.UUIDField()
    notifier_type = models.CharField(max_length=10)
    notifier_id = models.CharField(max_length=100)
    consent_id = models.CharField(max_length=100)
    consent_handle = models.CharField(max_length=100)
    consent_status = models.CharField(max_length=10,
                                      choices=[('ACTIVE', 'ACTIVE'), ('PENDING', 'PENDING'), ('REVOKED', 'REVOKED'),
                                               ('PAUSED', 'PAUSED'), ('REJECTED', 'REJECTED'), ('EXPIRED', 'EXPIRED')])


class FIStatusNotification(SoftDeletionModel):
    class Meta:
        db_table = "fi_status_notifications"

    ver = models.CharField(max_length=10)
    timestamp = models.DateTimeField()
    txnid = models.UUIDField(unique=True, editable=False)
    notifier_type = models.CharField(max_length=50)
    notifier_id = models.CharField(max_length=50)
    session_id = models.CharField(max_length=50)
    session_status = models.CharField(max_length=50)


class FIStatusResponse(SoftDeletionModel):
    class Meta:
        db_table = "fi_status_responses"

    fi_notification = models.CharField(max_length=50)
    fipID = models.CharField(max_length=50)


class Account(SoftDeletionModel):
    class Meta:
        db_table = "accounts"

    fi_status_response = models.CharField(max_length=50)
    link_ref_number = models.CharField(max_length=50)
    fi_status = models.CharField(max_length=50)
    description = models.TextField(blank=True)

class AccountAggregator(models.Model):
    aa_name = models.CharField(max_length=255)  # AA_NAME
    aa_base_path = models.CharField(max_length=255, blank=True)  # AA_BASE_PATH
    aa_webview_url = models.CharField(max_length=255, blank=True)  # AA_WEBVIEW_URL
    aa_vua_suffix = models.CharField(max_length=255, blank=True)  # AA_VUA_SUFFIX

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def generate_customer_vua(customer_phone, aa_suffix):
        # Assuming the helper function to generate customer_id is something like this
        return f"{customer_phone}{aa_suffix}"

    class Meta:
        db_table = 'account_aggregator'


class FIPData(models.Model):
    ver = models.CharField(max_length=10, null=True)
    timestamp = models.DateTimeField()
    txnid = models.CharField(max_length=255, null=True)
    requester_name = models.CharField(max_length=255)
    requester_id = models.CharField(max_length=255)
    entity_info_id = models.CharField(blank=True, null=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fip_data'
        indexes = [
            models.Index(fields=['entity_info_id'], name='fip_data_entity_info_id_idx'),
        ]

class SessionDetails(models.Model):
    id = models.AutoField(primary_key=True)
    session_id = models.CharField(max_length=100, default=None)
    session_status = models.CharField(max_length=20, default=None)
    consent_id = models.CharField(max_length=100)

    class Meta:
        db_table = "session_details"


class FIUEntity(models.Model):
    fiu_name = models.CharField(max_length=255)  # FIU NAME
    fiu_client_id = models.CharField(max_length=255, unique=True)  # FIU ID (on Sahamati CR)
    fiu_token_url = models.CharField(max_length=255)  # FIU TOKEN URL
    fiu_client_secret = models.CharField(max_length=255)  # FIU CLIENT SECRET
    rsa_key_json = models.JSONField() # RSA_KEY_JSON - Using JSONField
    pyro_token = models.CharField(max_length=255)  # PYRO TOKEN
    consent_redirection_url = models.CharField(max_length=255)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_registered_with(self, aa):
        # Check if there's a registration for this FIU with the given AA
        return FIUAARegistration.objects.filter(fiu=self, account_aggregator=aa).exists()

    class Meta:
        db_table = "fiu_entities"


class FIUCustomer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, blank=False)
    phone_number = models.CharField(max_length=255) 
    pan = models.CharField(max_length=50, blank=True)  # Replace 50 with the appropriate length for PAN
    email = models.EmailField(blank=True)
    fiu = models.ForeignKey('FIUEntity', on_delete=models.CASCADE, related_name='customers')  # Assuming FIUEntity is the correct model for FIU

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.id
    
    class Meta:
        db_table = "fiu_customers"


class ConsentStatus(models.TextChoices):
    INITIATED = 'INITIATED', 'Initiated'
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    PAUSED = 'PAUSED', 'Paused'
    REVOKED = 'REVOKED', 'Revoked'
    REJECTED = 'REJECTED', 'Rejected'

class ConsentDetail(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    consent_payload = models.JSONField() 
    fiu = models.ForeignKey(FIUEntity, on_delete=models.CASCADE, related_name='fiu_consents')
    aa = models.ForeignKey(AccountAggregator, on_delete=models.CASCADE, related_name='aa_consents')
    customer = models.ForeignKey(FIUCustomer, on_delete=models.CASCADE, related_name='customer_consents')  # ForeignKey to FIUCustomer
    consent_handle = models.UUIDField(default=uuid.uuid4, editable=False)
    consent_id = models.UUIDField(null=True, blank=True, default=None, editable=False)
    status = models.CharField(max_length=20, choices=ConsentStatus.choices, default=ConsentStatus.INITIATED)
    txnid = models.UUIDField(null=True, blank=True, default=None, editable=False)
    message = models.TextField(blank=True, default="")
    consent_details = models.JSONField(null=True)  
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)
    
    def to_dict(self):
        # Convert the model instance to a dict
        return model_to_dict(self, fields=[field.name for field in self._meta.fields])
    
    class Meta:
        db_table = "consent_details"
        indexes = [
            models.Index(fields=['consent_handle'], name='consent_handle_idx'),
        ]


class ConsentLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(FIUCustomer, on_delete=models.CASCADE, related_name='consent_logs')
    fiu = models.ForeignKey(FIUEntity, on_delete=models.CASCADE, related_name='consent_logs')
    aa = models.ForeignKey(AccountAggregator, on_delete=models.CASCADE, related_name='consent_logs')
    consent_handle = models.UUIDField(null=True, blank=True, default=None, editable=False)
    consent_id = models.UUIDField(null=True, blank=True, default=None, editable=False)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Log {self.id} for Customer {self.customer.id}"

    class Meta:
        db_table = "consent_logs"
        verbose_name_plural = "Consent Logs"


class FIDataRequest(models.Model):
    id = models.AutoField(primary_key=True)
    consent_id = models.ForeignKey(ConsentDetail, on_delete=models.CASCADE, related_name='fi_data_requests')
    customer_id = models.CharField(max_length=100, default=None)
    status = models.CharField(max_length=20, default='INITIATED')
    txnid = models.CharField(max_length=128, default="")
    session_id = models.CharField(max_length=128, default="")
    private_key = models.CharField(max_length=1024, default="")
    key_material = models.JSONField(null=True, blank=True)
    fetched_data = models.JSONField(null=True, blank=True) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)

    class Meta:
        db_table = "fi_data_requests"



class FIUAARegistration(models.Model):
    fiu = models.ForeignKey('FIUEntity', on_delete=models.CASCADE, related_name='aa_registrations')
    account_aggregator = models.ForeignKey('AccountAggregator', on_delete=models.CASCADE, related_name='fiu_registrations')
    fiu_aa_aes_token = models.CharField(max_length=255, blank=True, help_text="Token used by FIU/AA to encrypt/decrypt redirectURL")

    class Meta:
        db_table = 'fiu_aa_registration'
        unique_together = ('fiu', 'account_aggregator') 