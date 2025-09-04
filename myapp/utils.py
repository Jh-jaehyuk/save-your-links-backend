import boto3
import redis.client
from django.conf import settings


def get_redis_client(db=0):
    return redis.client.StrictRedis(host=settings.REDIS_HOST,
                                    password=settings.REDIS_PASS,
                                    db=db)

def get_boto3_client(service_name='s3'):
    client = boto3.client(
        service_name,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION_NAME,
    )

    return client