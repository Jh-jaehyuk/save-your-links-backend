from celery import shared_task
from django.conf import settings

from myapp.models import LinkCollectionViewModel, User
from myapp.utils import get_boto3_client


@shared_task
def save_view_model(collection_id, user_id):
    if LinkCollectionViewModel.objects.filter(collection_id=collection_id, viewer_id=user_id).exists():
        return

    LinkCollectionViewModel.objects.create(collection_id=collection_id, viewer_id=user_id)

@shared_task
def delete_s3_object(file_key):
    if not file_key:
        return

    try:
        s3_client = get_boto3_client()
        s3_client.delete_object(Bucket=settings.AWS_BUCKET_NAME, Key=file_key)
        print(f"Successfully deleted {file_key} from S3.")
    except Exception as e:
        print(f"Error deleting {file_key} from S3: {e}")
