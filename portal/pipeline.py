from social_core.pipeline.user import USER_FIELDS


def custom_create_user(backend, details, user=None, *args, **kwargs):
    # Check for existing user with verified email
    if user:
        if not user.is_email_verified:
            raise ValueError({"email error": "This account has not been verified. Check your email for a verification link."})
        else:
            return {"is_new": False}
        
    fields = {
        name: kwargs.get(name, details.get(name)) for name in backend.setting("USER_FIELDS", USER_FIELDS)
    }
    if not fields:
        return
    
    fields["is_email_verified"] = True
    fields["is_social_user"] = True
    user = backend.strategy.create_user(**fields)
    return {"is_new": True, "user": user}
        