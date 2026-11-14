"""Pure deterministic legacy account migration planning."""
from collections import defaultdict

def plan_accounts(rows, existing=()):
    groups = defaultdict(list)
    for row in rows:
        groups[row['email'].strip().casefold()].append(dict(row))
    reserved = set(groups)
    used = {v.strip().casefold() for a in existing for v in (a['username'], a['email'])}
    accounts = []
    for email, members in groups.items():
        tenants = [member['tenant_id'] for member in members]
        if len(set(tenants)) != len(tenants):
            raise ValueError(f'Conflicting memberships for {email}; resolve before migration')
        account = next((a for a in existing if a['email'].strip().casefold() == email), None)
        username = base = members[0]['username'].strip()
        suffix = 1
        group_ids = {member['id'] for member in members}
        group_tenants = {member['tenant_id'] for member in members}
        other_names = [(member['username'].strip().casefold(), member['tenant_id'])
                       for member in rows if member['id'] not in group_ids]
        while (username.casefold() in used
               or (username.casefold() in reserved and username.casefold() != email)
               or any(name == username.casefold() and (suffix > 1 or tenant in group_tenants)
                      for name, tenant in other_names)):
            suffix += 1
            username = f'{base}-{suffix}'
        if account is not None:
            username = account['username']
        used.add(username.casefold())
        used.add(email)
        accounts.append({'email': email, 'username': username, 'requires_recovery': bool(account['requires_password_reset']) if account is not None and 'requires_password_reset' in account.keys() else len(members) > 1,
                         'members': [{'id': m['id'], 'tenant_id': m['tenant_id'], 'old_username': m['username']} for m in members]})
    return accounts
