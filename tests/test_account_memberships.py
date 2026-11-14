from web.user_store import UserStore


def test_shared_identity_sessions_and_revocation(tmp_path):
    store = UserStore(tmp_path / "auth.db")
    for tenant in ("one", "two"):
        store.create_tenant(tenant, display_name=tenant)

    def create(tenant, password):
        return store.create_user(
            username="alice",
            email="alice@example.com",
            display_name="Alice",
            role="viewer",
            tenant_id=tenant,
            password_hash=password,
            password_salt="salt",
            must_change_password=False,
        )

    first = create("one", "original")
    second = create("two", "ignored")
    assert first.account_id == second.account_id
    assert second.password_hash == "original"
    raw, session = store.create_session(first.id)
    other, _ = store.create_session(first.id)
    store.switch_session_tenant(raw, "two")
    assert store.get_session_user(other).tenant_id == "one"
    store.update_user(second.id, disabled=True)
    assert store.get_session(raw)
    assert store.get_session_user(raw).tenant_id == ""
    store.update_account(first.account_id, display_name="Updated")
    assert store.get_user(second.id).display_name == "Updated"
    assert store.get_account_by_identifier(" ALICE@EXAMPLE.COM ").id == first.account_id


def test_historical_merge_invalidates_credentials_and_tokens(tmp_path):
    store = UserStore(tmp_path / "auth.db")
    for tenant in ("one", "two"):
        store.create_tenant(tenant, display_name=tenant)
    first = store.create_user(
        username="alice",
        email="alice@example.com",
        display_name="A",
        role="viewer",
        tenant_id="one",
        password_hash="original",
        password_salt="salt",
    )
    second = store.create_user(
        username="alice",
        email="alice@example.com",
        display_name="A",
        role="viewer",
        tenant_id="two",
        password_hash="ignored",
        password_salt="salt",
    )
    raw, _ = store.create_session(first.id)
    token = store.create_password_reset_token(first.id, "code")
    with store._connect() as conn:
        conn.execute("PRAGMA user_version=0")
        conn.execute("DELETE FROM accounts")
        conn.execute("UPDATE users SET account_id=NULL")
    store.ensure_schema()
    account = store.get_account_by_identifier("alice@example.com")
    assert account.requires_password_reset
    assert account.password_hash != "original"
    assert store.get_session(raw) is None
    assert store.get_password_reset_token(token.id) is None
    assert {m.id for m in store.list_account_memberships(account.id)} == {first.id, second.id}
    store.ensure_schema()
    assert store.get_account_user(account.id).password_hash == account.password_hash
    store.update_account(account.id, password_hash="new", password_salt="salt")
    assert not store.get_account_user(account.id).requires_password_reset


def test_global_identifier_collision_and_duplicate_membership(tmp_path):
    import pytest

    store = UserStore(tmp_path / "auth.db")
    for tenant in ("one", "two"):
        store.create_tenant(tenant, display_name=tenant)
    values = dict(
        username="alice",
        email="alice@example.com",
        display_name="A",
        role="viewer",
        password_hash="hash",
        password_salt="salt",
    )
    first = store.create_user(tenant_id="one", **values)
    with pytest.raises(ValueError):
        store.create_user(tenant_id="one", **values)
    with pytest.raises(ValueError):
        store.create_user(tenant_id="two", **{**values, "email": "other@example.com"})
    with pytest.raises(ValueError):
        store.update_account(first.account_id, email="")


def test_legacy_username_collisions_reserve_future_emails(tmp_path):
    store = UserStore(tmp_path / "auth.db")
    for tenant in ("one", "two", "three"):
        store.create_tenant(tenant, display_name=tenant)
    members = []
    for index, tenant in enumerate(("one", "two", "three")):
        members.append(
            store.create_user(
                username=f"user{index}",
                email=f"{index}@example.com",
                display_name="User",
                role="viewer",
                tenant_id=tenant,
                password_hash="hash",
                password_salt="salt",
            )
        )
    with store._connect() as conn:
        conn.execute("PRAGMA user_version=0")
        conn.execute("DELETE FROM accounts")
        conn.execute("UPDATE users SET account_id=NULL")
        conn.execute("UPDATE users SET username=? WHERE id=?", ("2@example.com", members[0].id))
        conn.execute("UPDATE users SET username=? WHERE id=?", ("same", members[1].id))
        conn.execute("UPDATE users SET username=? WHERE id=?", ("same", members[2].id))
    store.ensure_schema()
    first = store.get_account_by_identifier("0@example.com")
    assert first.username != "2@example.com"
    assert store.get_account_by_identifier("2@example.com").id == members[2].id
    second = store.get_account_by_identifier("1@example.com")
    third = store.get_account_by_identifier("2@example.com")
    assert second.username != third.username
    store.ensure_schema()
    assert store.get_account_user(first.id).username == first.username


def test_migration_suffix_avoids_unmigrated_membership_username(tmp_path):
    store = UserStore(tmp_path / "auth.db")
    for tenant in ("a", "b"):
        store.create_tenant(tenant, display_name=tenant)
    ids = []
    for index, tenant in enumerate(("a", "b", "b")):
        member = store.create_user(
            username=f"user{index}",
            email=f"e{index}@example.com",
            display_name="User",
            role="viewer",
            tenant_id=tenant,
            password_hash="hash",
            password_salt="salt",
        )
        ids.append(member.id)
    with store._connect() as conn:
        conn.execute("PRAGMA user_version=0")
        conn.execute("DELETE FROM accounts")
        conn.execute("UPDATE users SET account_id=NULL")
        for index, username in enumerate(("x", "x", "x-2")):
            conn.execute(
                "UPDATE users SET username=?,created_at=? WHERE id=?",
                (username, index + 1, ids[index]),
            )
    store.ensure_schema()
    assert store.get_account_by_identifier("e0@example.com").username == "x"
    assert store.get_account_by_identifier("e1@example.com").username == "x-3"
    assert store.get_account_by_identifier("e2@example.com").username == "x-2"
    store.ensure_schema()
    assert store.get_user(ids[1]).username == "x-3"


def test_session_fallback_becomes_last_visited_tenant(tmp_path):
    store = UserStore(tmp_path / "auth.db")
    members = []
    for tenant in ("a", "b"):
        store.create_tenant(tenant, display_name=tenant)
        members.append(
            store.create_user(
                username="alice",
                email="alice@example.com",
                display_name="Alice",
                role="viewer",
                tenant_id=tenant,
                password_hash="hash",
                password_salt="salt",
            )
        )
    raw, _ = store.create_session(members[0].id)
    store.switch_session_tenant(raw, "b")
    store.update_user(members[1].id, disabled=True)
    fallback, _ = store.create_session(members[0].account_id)
    assert store.get_session_user(fallback).tenant_id == "a"
    store.update_user(members[1].id, disabled=False)
    later, _ = store.create_session(members[0].account_id)
    assert store.get_session_user(later).tenant_id == "a"
