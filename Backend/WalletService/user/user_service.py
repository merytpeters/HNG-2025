from .crud import UserCRUD
from .schemas import UserCreateOut, GoogleIDTokenSchema
from sqlalchemy.orm import Session
from WalletService.auth.service import GoogleIDTokenService

google_service = GoogleIDTokenService()


class UserService(UserCRUD):
    def __init__(self, model):
        super().__init__(model)

    def create_or_get_user(
        self, google_token: GoogleIDTokenSchema, db: Session
    ) -> UserCreateOut:
        try:
            google_service.validate_email(google_token)
            google_service.verify_token(google_token)
            user = self.get_or_create_by_google_token(db, google_token)
            return google_service.issue_internal_jwt(user)
        except Exception as e:
            raise Exception(f"Failed to create or get user: {str(e)}")
