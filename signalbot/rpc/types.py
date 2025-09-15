from pydantic import BaseModel

class SignalRPCGroupUser(BaseModel):
    number: str | None
    uuid: str | None

class SignalRPCGroup(BaseModel):
    id: str
    name: str
    description: str
    isMember: bool
    isBlocked: bool
    messageExpirationTime: int
    members: list[SignalRPCGroupUser]
    pendingMembers: list[SignalRPCGroupUser]
    requestingMembers: list[SignalRPCGroupUser]
    admins: list[SignalRPCGroupUser]
    banned: list[SignalRPCGroupUser]
    permissionAddMember: str
    permissionEditDetails: str
    permissionSendMessage: str
    groupInviteLink: str | None

class SignalRPCProfile(BaseModel):
    lastUpdateTimestamp: int
    givenName: str | None
    familyName: str | None
    about: str | None
    aboutEmoji: str | None
    hasAvatar: bool
    mobileCoinAddress: str | None

class SignalRPCContact(BaseModel):
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
    profile: SignalRPCProfile | None
