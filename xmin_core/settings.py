from functools import cached_property

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from rasterio.session import AWSSession

class RasterS3Settings(BaseSettings):
    s3_endpoint: str
    s3_access_key: str
    s3_secret_key: SecretStr
    s3_bucket: str
    s3_pop_filename: str

    model_config = SettingsConfigDict(env_file='.env')

    @cached_property
    def s3_client(self) -> AWSSession:
        session = AWSSession(
            endpoint_url=self.s3_endpoint,
            aws_access_key_id=self.s3_access_key,
            aws_secret_access_key=self.s3_secret_key.get_secret_value(),
        )

        return session

    @cached_property
    def pop_raster_url(self) -> str:
        return f's3://{self.s3_bucket}/{self.s3_pop_filename}'
