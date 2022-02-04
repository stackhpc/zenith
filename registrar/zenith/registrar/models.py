import secrets
import string
import typing as t

from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives.serialization import load_ssh_public_key

from pydantic import BaseModel, Field, conset, constr, validator

from .config import settings, SSHPublicKeyType


#: Constraint for a Zenith subdomain
#: Subdomains must be at most 63 characters long, can only contain alphanumeric characters
#: and hyphens, and cannot start or end with a hyphen
#: In addition, this will eventually become a Kubernetes service name and Kubernetes service
#: names must start with a letter and be lower case
#: See https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#rfc-1035-label-names
Subdomain = constr(regex = r"^[a-z][a-z0-9-]*?[a-z0-9]$", max_length = 63)


class SSHPublicKey(str):
    """
    Custom type for an SSH public key.
    """
    @classmethod
    def __get_validators__(cls):
        """
        Returns the Pydantic validators for this class.
        """
        yield cls.validate

    @classmethod
    def validate(cls, v):
        """
        Validates the given value as an SSH public key.
        """
        # Try to load the public key using cryptography
        try:
            public_key = load_ssh_public_key(v.encode())
        except (ValueError, UnsupportedAlgorithm):
            raise ValueError("Not a valid SSH public key.")
        # Now we know it is a valid SSH key, we can get the type as a string
        key_type = v.split()[0]
        # Test whether the key type is an allowed key type
        if key_type not in settings.ssh_allowed_key_types:
            raise ValueError(f"Keys of type '{key_type}' are not permitted.")
        # If the key is an RSA key, check the minimum size
        if key_type == SSHPublicKeyType.RSA and public_key.key_size < settings.ssh_rsa_min_bits:
            message = "RSA keys must have a minimum of {} bits ({} given).".format(
                settings.ssh_rsa_min_bits,
                public_key.key_size
            )
            raise ValueError(message)
        # The key is valid! Hooray!
        return cls(v)


def default_subdomain():
    """
    Returns a random subdomain consisting of 63 alphanumeric characters that will also be
    a valid Kubernetes service name.
    """
    # Domains must start with a letter
    chars = [secrets.choice(string.ascii_lowercase)]
    chars.extend(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(62))
    return "".join(chars)


class ReservationRequest(BaseModel):
    """
    Model for a request to reserve a subdomain.
    """
    #: The subdomain to reserve
    subdomain: Subdomain = Field(default_factory = default_subdomain)
    #: The public keys to associate with the subdomain
    public_keys: t.Optional[conset(SSHPublicKey, min_items = 1)] = None

    @validator("subdomain")
    def validate_subdomain(cls, v):
        """
        Validates that the subdomain is not one of the reserved subdomains.
        """
        if v in settings.reserved_subdomains:
            raise ValueError(f"'{v}' is a reserved subdomain")
        return v


class Reservation(BaseModel):
    """
    Model for a successful reservation.
    """
    #: The subdomain that was reserved
    subdomain: Subdomain
    #: The FQDN for the subdomain that was reserved
    fqdn: constr(min_length = 1)
    #: The token to use to associate public keys with the subdomain if no keys were given
    token: t.Optional[str] = None
    #: The fingerprints of any keys that were registered
    fingerprints: t.List[str] = Field(default_factory = list)


class VerificationRequest(BaseModel):
    """
    Model for a request to verify that a public key has an associated subdomain.
    """
    #: The public key to check
    public_key: SSHPublicKey


class VerificationResult(BaseModel):
    """
    Model for a verification result indicating the associated subdomain for a public key.
    """
    #: The associated subdomain
    subdomain: Subdomain
    #: The public key
    public_key: SSHPublicKey


class PublicKeyAssociationRequest(BaseModel):
    """
    Model for a request to associate public keys with a subdomain.
    """
    #: The token for the request
    token: constr(min_length = 1)
    #: The public keys to associate with the subdomain
    public_keys: conset(SSHPublicKey, min_items = 1)


class PublicKeyAssociation(BaseModel):
    """
    Model for a successful public key association.
    """
    #: The subdomain that the keys were associated with
    subdomain: str
    #: The fingerprints of the public keys that weere associated with the subdomain
    fingerprints: t.List[str]


class Error(BaseModel):
    """
    Model for an error response.
    """
    #: The error message
    detail: str