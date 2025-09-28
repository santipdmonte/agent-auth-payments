from schemas.users_schemas import UserUpdate
from fastapi import Depends
from database import get_db
from models.users_models import User, UserRole, UserSocialAccount, UserPhone
from sqlalchemy.orm import Session
from models.users_models import AuthProviderType
from uuid import UUID
from services.tokens_service import get_token_service, TokenService
from datetime import timedelta
import os
from dotenv import load_dotenv
from utils.email_utlis import send_phone_number_verification_email_utils
from models.code_validation_models import PhoneEmailVerificationCode
from datetime import datetime, timezone
import random

load_dotenv()

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
PHONE_EMAIL_CODE_EXPIRE_MINUTES = int(os.getenv("PHONE_EMAIL_CODE_EXPIRE_MINUTES", "10"))

class UserService:
    """Service class for user CRUD operations and business logic"""
    
    def __init__(self, db: Depends(get_db)):
        self.db = db
        self.token_service: TokenService = get_token_service(db)

    # ==================== USER METHODS ====================

    def create_user(self, user: User):

        exists_user = self.get_user_by_email(user.email)
        if exists_user:
            return exists_user

        self.db.add(user)
        self.db.commit()
        return user

    def get_user(self, user_id: UUID):
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_email(self, email: str):
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_phone_number(self, phone_number: str):
        return (
            self.db.query(User)
            .filter(User.phones.any(UserPhone.phone == phone_number))
            .first()
        )

    def get_all_users(self):
        return self.db.query(User).filter(User.disabled == False).all()

    def get_all_phone_numbers(self):
        return self.db.query(UserPhone).all()

    def update_user(self, user: User, user_update: UserUpdate):
        user_update = user_update.model_dump(exclude_unset=True)
        for key, value in user_update.items():
            setattr(user, key, value)

        self.db.commit()
        self.db.refresh(user)

        return user

    def delete_user(self, user: User):
        self.db.delete(user)
        self.db.commit()
        return user

    def get_user_social_accounts(self, user: User):
        return user.social_accounts

    def get_user_social_account(self, provider_id: str):
        return self.db.query(UserSocialAccount).filter(UserSocialAccount.provider_id == provider_id).first()

    def make_user_admin(self, user: User):
        user.role = UserRole.ADMIN
        self.db.commit()
        self.db.refresh(user)
        return user

    def _create_user_social_account(self, user_social_account: UserSocialAccount):
        self.db.add(user_social_account)
        self.db.commit()
        self.db.refresh(user_social_account)
        return user_social_account

    def process_google_login(self, user_info: dict):

        user = self.get_user_by_email(user_info['email'])
        if not user:
            user = User(
                email=user_info['email'],
                full_name=user_info['name'],
                given_name=user_info['given_name'],
                family_name=user_info['family_name'],
                picture=user_info['picture'],
            )
            self.create_user(user)
        else:
            user_update = UserUpdate(
                full_name=user.full_name or user_info['name'] ,
                given_name=user.given_name or user_info['given_name'] ,
                family_name=user.family_name or user_info['family_name'] ,
                picture=user.picture or user_info['picture'],
            )
            self.update_user(user, user_update)

        user_social_account = self.get_user_social_account(user_info['sub'])
        if not user_social_account:
            user_social_account = UserSocialAccount(
                user_id=user.id,
                provider=AuthProviderType.GOOGLE,
                provider_id=user_info['sub'],
                email=user_info['email'],
                is_verified=user_info['email_verified'],
                name=user_info['name'],
                given_name=user_info['given_name'],
                family_name=user_info['family_name'],
                picture=user_info['picture'],
            )
            self._create_user_social_account(user_social_account)
            
        else:
            user_social_account.update_last_used()
            self.db.commit()


        # Create new app access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self.token_service.create_access_token(
            data={"sub": user_info['email']}, expires_delta=access_token_expires
        )
        refresh_token = self.token_service.create_refresh_token(data={"sub": user_info['email']})
        return access_token, refresh_token

    def get_phone_number_verification_email_code(self, phone_number: str, email: str) -> str:
        # Generate a 6-digit numeric code
        code = f"{random.randint(0, 999999):06d}"

        created_at = datetime.now(timezone.utc)
        expires_at = created_at + timedelta(minutes=PHONE_EMAIL_CODE_EXPIRE_MINUTES)

        # Persist the verification record
        verification = PhoneEmailVerificationCode(
            email=email,
            phone_number=phone_number,
            code=code,
            created_at=created_at,
            expires_at=expires_at,
        )
        self.db.add(verification)
        self.db.commit()

        # Send the code via email
        send_phone_number_verification_email_utils(email, code)
        return code


    def validate_phone_number_verification_code(self, email: str, phone_number: str, code: str) -> dict:
        now = datetime.now(timezone.utc)
        verification = (
            self.db.query(PhoneEmailVerificationCode)
            .filter(
                PhoneEmailVerificationCode.email == email,
                PhoneEmailVerificationCode.phone_number == phone_number,
                PhoneEmailVerificationCode.code == code,
                PhoneEmailVerificationCode.expires_at > now,
                PhoneEmailVerificationCode.used_at.is_(None),
            )
            .order_by(PhoneEmailVerificationCode.created_at.desc())
            .first()
        )

        if not verification:
            return {"error": "Invalid or expired code"}
        
        user_service = UserService(self.db)
        user = user_service.get_user_by_email(email)
        if not user:
            user = User(email=email)
            user = user_service.create_user(user)

        # Check if the phone already exists
        existing_phone = (
            self.db.query(UserPhone)
            .filter(UserPhone.phone == phone_number)
            .first()
        )

        if existing_phone:
            # If it already belongs to the same user, ensure it's verified
            if existing_phone.user_id == user.id:
                if not existing_phone.is_verified:
                    existing_phone.is_verified = True
                    self.db.commit()
                    self.db.refresh(existing_phone)
                return user
            # If it belongs to another user, do not reassign to avoid UNIQUE violations
            return {"error": "Phone number already in use by another user"}

        # Create a phone number for the user if it does not exist yet
        new_phone = UserPhone(phone=phone_number, user_id=user.id, is_verified=True)
        self.db.add(new_phone)

        # mark verification as used
        verification.used_at = now
        self.db.commit()
        self.db.refresh(new_phone)

        return user

# ==================== DEPENDENCY INJECTION ====================

def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """Dependency injection for UserService"""
    return UserService(db)