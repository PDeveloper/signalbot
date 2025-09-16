from pydantic import BaseModel

class SignalGroupUser(BaseModel):
    number: str | None
    uuid: str | None

class SignalGroupExtended(BaseModel):
    id: str
    name: str
    description: str
    isMember: bool
    isBlocked: bool
    messageExpirationTime: int
    members: list[SignalGroupUser]
    pendingMembers: list[SignalGroupUser]
    requestingMembers: list[SignalGroupUser]
    admins: list[SignalGroupUser]
    banned: list[SignalGroupUser]
    permissionAddMember: str
    permissionEditDetails: str
    permissionSendMessage: str
    groupInviteLink: str | None

class SignalProfileExtended(BaseModel):
    lastUpdateTimestamp: int
    givenName: str | None
    familyName: str | None
    about: str | None
    aboutEmoji: str | None
    hasAvatar: bool
    mobileCoinAddress: str | None

class SignalContactExtended(BaseModel):
    number: str | None
    uuid: str | None
    username: str | None
    name: str
    givenName: str | None
    familyName: str | None
    nickName: str | None
    nickGivenName: str | None
    nickFamilyName: str | None
    note: str | None
    color: str | None
    isBlocked: bool
    isHidden: bool
    messageExpirationTime: int
    profileSharing: bool
    unregistered: bool
    profile: SignalProfileExtended | None
