from datetime import datetime, timezone
from WalletService.apikey.apikey_service import APIKeyService
from WalletService.user.models import APIKey as APIKeyModel, WalletUser, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def setup_in_memory_db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_list_user_keys_permission_shape():
    db = setup_in_memory_db()
    svc = APIKeyService()

    # create user
    user_id = "user-test-1"
    u = WalletUser(id=user_id, name="Test", email="test@example.com", google_sub=None)
    db.add(u)
    db.commit()

    # create API key row with permissions stored as simple strings
    now = datetime.now(timezone.utc)
    ak = APIKeyModel(
        name="k1",
        walletuser_id=user_id,
        hashed_secret="hash",
        permissions=["deposit", "read"],
        expires_at=now,
        created_at=now,
        revoked=False,
    )
    db.add(ak)
    db.commit()

    res = svc.list_user_keys(db, user_id)
    assert isinstance(res, list)
    assert len(res) == 1
    out = res[0]
    as_dict = out.dict()
    perms = as_dict.get("permissions")
    assert isinstance(perms, list)
    assert len(perms) == 2
    for p in perms:
        # each permission should be an object/dict with 'type' key and string value
        assert isinstance(p, dict)
        assert "type" in p
        assert isinstance(p["type"], str)
