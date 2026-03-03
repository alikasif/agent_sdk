"""Unit tests for agent_sdk.isolation: scope, validator, filter."""
import pytest
from agent_sdk.isolation import (
    set_user_scope, get_user_scope, clear_user_scope,
    ScopedQueryBuilder, IsolationValidator
)
from agent_sdk.exceptions import IsolationViolationError

TEST_USER_ID = "test-user-001"
TEST_USER_ID_2 = "test-user-002"

def test_set_get_clear_user_scope():
    token = set_user_scope(TEST_USER_ID)
    assert get_user_scope() == TEST_USER_ID
    clear_user_scope(token)
    with pytest.raises(IsolationViolationError):
        get_user_scope()

def test_isolation_violation_error():
    with pytest.raises(IsolationViolationError):
        get_user_scope()

def test_scoped_query_builder_select():
    token = set_user_scope(TEST_USER_ID)
    qb = ScopedQueryBuilder()
    sql, params = qb.select("foo")
    assert "user_id = ?" in sql
    assert params[0] == TEST_USER_ID
    clear_user_scope(token)

def test_scoped_query_builder_insert():
    token = set_user_scope(TEST_USER_ID)
    qb = ScopedQueryBuilder()
    sql, params = qb.insert("bar", {"x": 1})
    assert "user_id" in sql
    assert params[-1] == TEST_USER_ID
    clear_user_scope(token)

def test_isolation_validator_assert_owns():
    record = {"user_id": TEST_USER_ID}
    IsolationValidator.assert_owns(record, TEST_USER_ID)
    with pytest.raises(IsolationViolationError):
        IsolationValidator.assert_owns({"user_id": TEST_USER_ID_2}, TEST_USER_ID)

def test_isolation_validator_assert_all_owned():
    records = [{"user_id": TEST_USER_ID}, {"user_id": TEST_USER_ID}]
    IsolationValidator.assert_all_owned(records, TEST_USER_ID)
    with pytest.raises(IsolationViolationError):
        IsolationValidator.assert_all_owned([{"user_id": TEST_USER_ID}, {"user_id": TEST_USER_ID_2}], TEST_USER_ID)
