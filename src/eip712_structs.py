"""
This is basically the code from here https://github.com/ConsenSysMesh/py-eip712-structs merged into 1 file

The reason this is done is because we want to use Python3.11+ and the library only supports 3.6
The library requires pysha library which can not be installed on 3.11
"""
import functools
import json
import operator
import re
from collections import OrderedDict, defaultdict
from json import JSONEncoder
from typing import Any, List, NamedTuple, Tuple, Type, Union

from eth_utils.conversions import to_bytes, to_hex, to_int
from eth_utils.crypto import keccak

default_domain = None


class EIP712Type:
    """The base type for members of a struct.

    Generally you wouldn't use this - instead, see the subclasses below. Or you may want an EIP712Struct instead.
    """

    def __init__(self, type_name: str, none_val: Any):
        self.type_name = type_name
        self.none_val = none_val

    def encode_value(self, value) -> bytes:
        """Given a value, verify it and convert into the format required by the spec.

        :param value: A correct input value for the implemented type.
        :return: A 32-byte object containing encoded data
        """
        if value is None:
            return self._encode_value(self.none_val)
        else:
            return self._encode_value(value)

    def _encode_value(self, value) -> bytes:
        """Must be implemented by subclasses, handles value encoding on a case-by-case basis.

        Don't call this directly - use ``.encode_value(value)`` instead.
        """
        pass

    def __eq__(self, other):
        self_type = getattr(self, "type_name")
        other_type = getattr(other, "type_name")

        return self_type is not None and self_type == other_type

    def __hash__(self):
        return hash(self.type_name)


class Array(EIP712Type):
    def __init__(
        self, member_type: Union[EIP712Type, Type[EIP712Type]], fixed_length: int = 0
    ):
        """Represents an array member type.

        Example:
            a1 = Array(String())     # string[] a1
            a2 = Array(String(), 8)  # string[8] a2
            a3 = Array(MyStruct)     # MyStruct[] a3
        """
        fixed_length = int(fixed_length)
        if fixed_length == 0:
            type_name = f"{member_type.type_name}[]"
        else:
            type_name = f"{member_type.type_name}[{fixed_length}]"
        self.member_type = member_type
        self.fixed_length = fixed_length
        super(Array, self).__init__(type_name, [])

    def _encode_value(self, value):
        """Arrays are encoded by concatenating their encoded contents, and taking the keccak256 hash."""
        encoder = self.member_type
        encoded_values = [encoder.encode_value(v) for v in value]
        return keccak(b"".join(encoded_values))


class Address(EIP712Type):
    def __init__(self):
        """Represents an ``address`` type."""
        super(Address, self).__init__("address", 0)

    def _encode_value(self, value):
        """Addresses are encoded like Uint160 numbers."""

        # Some smart conversions - need to get the address to a numeric before we encode it
        if isinstance(value, bytes):
            v = to_int(value)
        elif isinstance(value, str):
            v = to_int(hexstr=value)
        else:
            v = value  # Fallback, just use it as-is.
        return Uint(160).encode_value(v)


class Boolean(EIP712Type):
    def __init__(self):
        """Represents a ``bool`` type."""
        super(Boolean, self).__init__("bool", False)

    def _encode_value(self, value):
        """Booleans are encoded like the uint256 values of 0 and 1."""
        if value is False:
            return Uint(256).encode_value(0)
        elif value is True:
            return Uint(256).encode_value(1)
        else:
            raise ValueError(f"Must be True or False. Got: {value}")


class Bytes(EIP712Type):
    def __init__(self, length: int = 0):
        """Represents a solidity bytes type.

        Length may be used to specify a static ``bytesN`` type. Or 0 for a dynamic ``bytes`` type.
        Example:
            b1 = Bytes()    # bytes b1
            b2 = Bytes(10)  # bytes10 b2

        ``length`` MUST be between 0 and 32, or a ValueError is raised.
        """
        length = int(length)
        if length == 0:
            # Special case: Length of 0 means a dynamic bytes type
            type_name = "bytes"
        elif 1 <= length <= 32:
            type_name = f"bytes{length}"
        else:
            raise ValueError(f"Byte length must be between 1 or 32. Got: {length}")
        self.length = length
        super(Bytes, self).__init__(type_name, b"")

    def _encode_value(self, value):
        """Static bytesN types are encoded by right-padding to 32 bytes. Dynamic bytes types are keccak256 hashed."""
        if isinstance(value, str):
            # Try converting to a bytestring, assuming that it's been given as hex
            value = to_bytes(hexstr=value)

        if self.length == 0:
            return keccak(value)
        else:
            if len(value) > self.length:
                raise ValueError(
                    f"{self.type_name} was given bytes with length {len(value)}"
                )
            padding = bytes(32 - len(value))
            return value + padding


class Int(EIP712Type):
    def __init__(self, length: int = 256):
        """Represents a signed int type. Length may be given to specify the int length in bits. Default length is 256

        Example:
            i1 = Int(256)  # int256 i1
            i2 = Int()     # int256 i2
            i3 = Int(128)  # int128 i3
        """
        length = int(length)
        if length < 8 or length > 256 or length % 8 != 0:
            raise ValueError(
                f"Int length must be a multiple of 8, between 8 and 256. Got: {length}"
            )
        self.length = length
        super(Int, self).__init__(f"int{length}", 0)

    def _encode_value(self, value: int):
        """Ints are encoded by padding them to 256-bit representations."""
        value.to_bytes(self.length // 8, byteorder="big", signed=True)  # For validation
        return value.to_bytes(32, byteorder="big", signed=True)


class String(EIP712Type):
    def __init__(self):
        """Represents a string type."""
        super(String, self).__init__("string", "")

    def _encode_value(self, value):
        """Strings are encoded by taking the keccak256 hash of their contents."""
        return keccak(text=value)


class Uint(EIP712Type):
    def __init__(self, length: int = 256):
        """Represents an unsigned int type. Length may be given to specify the int length in bits. Default length is 256

        Example:
            ui1 = Uint(256)  # uint256 ui1
            ui2 = Uint()     # uint256 ui2
            ui3 = Uint(128)  # uint128 ui3
        """
        length = int(length)
        if length < 8 or length > 256 or length % 8 != 0:
            raise ValueError(
                f"Uint length must be a multiple of 8, between 8 and 256. Got: {length}"
            )
        self.length = length
        super(Uint, self).__init__(f"uint{length}", 0)

    def _encode_value(self, value: int):
        """Uints are encoded by padding them to 256-bit representations."""
        value.to_bytes(
            self.length // 8, byteorder="big", signed=False
        )  # For validation
        return value.to_bytes(32, byteorder="big", signed=False)


# This helper dict maps solidity's type names to our EIP712Type classes
solidity_type_map = {
    "address": Address,
    "bool": Boolean,
    "bytes": Bytes,
    "int": Int,
    "string": String,
    "uint": Uint,
}


def from_solidity_type(solidity_type: str):
    """Convert a string into the EIP712Type implementation. Basic types only."""
    pattern = r"([a-z]+)(\d+)?(\[(\d+)?\])?"
    match = re.match(pattern, solidity_type)

    if match is None:
        return None

    type_name = match.group(1)  # The type name, like the "bytes" in "bytes32"
    opt_len = match.group(2)  # An optional length spec, like the "32" in "bytes32"
    is_array = match.group(3)  # Basically just checks for square brackets
    array_len = match.group(4)  # For fixed length arrays only, this is the length

    if type_name not in solidity_type_map:
        # Only supporting basic types here - return None if we don't recognize it.
        return None

    # Construct the basic type
    base_type = solidity_type_map[type_name]
    if opt_len:
        type_instance = base_type(int(opt_len))
    else:
        type_instance = base_type()

    if is_array:
        # Nest the aforementioned basic type into an Array.
        if array_len:
            result = Array(type_instance, int(array_len))
        else:
            result = Array(type_instance)
        return result
    else:
        return type_instance


class OrderedAttributesMeta(type):
    """Metaclass to ensure struct attribute order is preserved."""

    @classmethod
    def __prepare__(mcs, name, bases):
        return OrderedDict()


class EIP712Struct(EIP712Type, metaclass=OrderedAttributesMeta):
    """A representation of an EIP712 struct. Subclass it to use it.

    Example:
        from eip712_structs import EIP712Struct, String

        class MyStruct(EIP712Struct):
            some_param = String()

        struct_instance = MyStruct(some_param='some_value')
    """

    def __init__(self, **kwargs):
        super(EIP712Struct, self).__init__(self.type_name, None)
        members = self.get_members()
        self.values = dict()
        for name, typ in members:
            value = kwargs.get(name)
            if isinstance(value, dict):
                value = typ(**value)
            self.values[name] = value

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.type_name = cls.__name__

    def encode_value(self, value=None):
        """Returns the struct's encoded value.

        A struct's encoded value is a concatenation of the bytes32 representation of each member of the struct.
        Order is preserved.

        :param value: This parameter is not used for structs.
        """
        encoded_values = list()
        for name, typ in self.get_members():
            if isinstance(typ, type) and issubclass(typ, EIP712Struct):
                # Nested structs are recursively hashed, with the resulting 32-byte hash appended to the list of values
                sub_struct = self.get_data_value(name)
                encoded_values.append(sub_struct.hash_struct())
            else:
                # Regular types are encoded as normal
                encoded_values.append(typ.encode_value(self.values[name]))
        return b"".join(encoded_values)

    def get_data_value(self, name):
        """Get the value of the given struct parameter."""
        return self.values.get(name)

    def set_data_value(self, name, value):
        """Set the value of the given struct parameter."""
        if name in self.values:
            self.values[name] = value

    def data_dict(self):
        """Provide the entire data dictionary representing the struct.

        Nested structs instances are also converted to dict form.
        """
        result = dict()
        for k, v in self.values.items():
            if isinstance(v, EIP712Struct):
                result[k] = v.data_dict()
            else:
                result[k] = v
        return result

    @classmethod
    def _encode_type(cls, resolve_references: bool) -> str:
        member_sigs = [f"{typ.type_name} {name}" for name, typ in cls.get_members()]
        struct_sig = f'{cls.type_name}({",".join(member_sigs)})'

        if resolve_references:
            reference_structs = set()
            cls._gather_reference_structs(reference_structs)
            sorted_structs = sorted(
                list(s for s in reference_structs if s != cls),
                key=lambda s: s.type_name,
            )
            for struct in sorted_structs:
                struct_sig += struct._encode_type(resolve_references=False)
        return struct_sig

    @classmethod
    def _gather_reference_structs(cls, struct_set):
        """Finds reference structs defined in this struct type, and inserts them into the given set."""
        structs = [
            m[1]
            for m in cls.get_members()
            if isinstance(m[1], type) and issubclass(m[1], EIP712Struct)
        ]
        for struct in structs:
            if struct not in struct_set:
                struct_set.add(struct)
                struct._gather_reference_structs(struct_set)

    @classmethod
    def encode_type(cls):
        """Get the encoded type signature of the struct.

        Nested structs are also encoded, and appended in alphabetical order.
        """
        return cls._encode_type(True)

    @classmethod
    def type_hash(cls) -> bytes:
        """Get the keccak hash of the struct's encoded type."""
        return keccak(text=cls.encode_type())

    def hash_struct(self) -> bytes:
        """The hash of the struct.

        hash_struct => keccak(type_hash || encode_data)
        """
        return keccak(b"".join([self.type_hash(), self.encode_value()]))

    @classmethod
    def get_members(cls) -> List[Tuple[str, EIP712Type]]:
        """A list of tuples of supported parameters.

        Each tuple is (<parameter_name>, <parameter_type>). The list's order is determined by definition order.
        """
        members = [
            m
            for m in cls.__dict__.items()
            if isinstance(m[1], EIP712Type)
            or (isinstance(m[1], type) and issubclass(m[1], EIP712Struct))
        ]
        return members

    @staticmethod
    def _assert_domain(domain):
        result = domain or eip712_structs.default_domain
        if not result:
            raise ValueError(
                "Domain must be provided, or eip712_structs.default_domain must be set."
            )
        return result

    def to_message(self, domain: "EIP712Struct" = None) -> dict:
        """Convert a struct into a dictionary suitable for messaging.

        Dictionary is of the form:
            {
                'primaryType': Name of the primary type,
                'types': Definition of each included struct type (including the domain type)
                'domain': Values for the domain struct,
                'message': Values for the message struct,
            }

        :returns: This struct + the domain in dict form, structured as specified for EIP712 messages.
        """
        domain = self._assert_domain(domain)
        structs = {domain, self}
        self._gather_reference_structs(structs)

        # Build type dictionary
        types = dict()
        for struct in structs:
            members_json = [
                {
                    "name": m[0],
                    "type": m[1].type_name,
                }
                for m in struct.get_members()
            ]
            types[struct.type_name] = members_json

        result = {
            "primaryType": self.type_name,
            "types": types,
            "domain": domain.data_dict(),
            "message": self.data_dict(),
        }

        return result

    def to_message_json(self, domain: "EIP712Struct" = None) -> str:
        message = self.to_message(domain)
        return json.dumps(message, cls=BytesJSONEncoder)

    def signable_bytes(self, domain: "EIP712Struct" = None) -> bytes:
        """Return a ``bytes`` object suitable for signing, as specified for EIP712.

        As per the spec, bytes are constructed as follows:
            ``b'\x19\x01' + domain_hash_bytes + struct_hash_bytes``

        :param domain: The domain to include in the hash bytes. If None, uses ``eip712_structs.default_domain``
        :return: The bytes object
        """
        domain = self._assert_domain(domain)
        result = b"\x19\x01" + domain.hash_struct() + self.hash_struct()
        return result

    @classmethod
    def from_message(cls, message_dict: dict) -> "StructTuple":
        """Convert a message dictionary into two EIP712Struct objects - one for domain, another for the message struct.

        Returned as a StructTuple, which has the attributes ``message`` and ``domain``.

        Example:
            my_msg = { .. }
            deserialized = EIP712Struct.from_message(my_msg)
            msg_struct = deserialized.message
            domain_struct = deserialized.domain

        :param message_dict: The dictionary, such as what is produced by EIP712Struct.to_message.
        :return: A StructTuple object, containing the message and domain structs.
        """
        structs = dict()
        unfulfilled_struct_params = defaultdict(list)

        for type_name in message_dict["types"]:
            # Dynamically construct struct class from dict representation
            StructFromJSON = type(type_name, (EIP712Struct,), {})

            for member in message_dict["types"][type_name]:
                # Either a basic solidity type is set, or None if referring to a reference struct (we'll fill it later)
                member_name = member["name"]
                member_sol_type = from_solidity_type(member["type"])
                setattr(StructFromJSON, member_name, member_sol_type)
                if member_sol_type is None:
                    # Track the refs we'll need to set later.
                    unfulfilled_struct_params[type_name].append(
                        (member_name, member["type"])
                    )

            structs[type_name] = StructFromJSON

        # Now that custom structs have been parsed, pass through again to set the references
        for struct_name, unfulfilled_member_names in unfulfilled_struct_params.items():
            regex_pattern = r"([a-zA-Z0-9_]+)(\[(\d+)?\])?"

            struct_class = structs[struct_name]
            for name, type_name in unfulfilled_member_names:
                match = re.match(regex_pattern, type_name)
                base_type_name = match.group(1)
                ref_struct = structs[base_type_name]
                if match.group(2):
                    # The type is an array of the struct
                    arr_len = (
                        match.group(3) or 0
                    )  # length of 0 means the array is dynamically sized
                    setattr(struct_class, name, Array(ref_struct, arr_len))
                else:
                    setattr(struct_class, name, ref_struct)

        primary_struct = structs[message_dict["primaryType"]]
        domain_struct = structs["EIP712Domain"]

        primary_result = primary_struct(**message_dict["message"])
        domain_result = domain_struct(**message_dict["domain"])
        result = StructTuple(message=primary_result, domain=domain_result)

        return result

    @classmethod
    def _assert_key_is_member(cls, key):
        member_names = {tup[0] for tup in cls.get_members()}
        if key not in member_names:
            raise KeyError(f'"{key}" is not defined for this struct.')

    @classmethod
    def _assert_property_type(cls, key, value):
        """Eagerly check for a correct member type"""
        members = dict(cls.get_members())
        typ = members[key]

        if isinstance(typ, type) and issubclass(typ, EIP712Struct):
            # We expect an EIP712Struct instance. Assert that's true, and check the struct signature too.
            if not isinstance(value, EIP712Struct) or value._encode_type(
                False
            ) != typ._encode_type(False):
                raise ValueError(
                    f"Given value is of type {type(value)}, but we expected {typ}"
                )
        else:
            # Since it isn't a nested struct, its an EIP712Type
            try:
                typ.encode_value(value)
            except Exception as e:
                raise ValueError(
                    f"The python type {type(value)} does not appear "
                    f"to be supported for data type {typ}."
                ) from e

    def __getitem__(self, key):
        """Provide access directly to the underlying value dictionary"""
        self._assert_key_is_member(key)
        return self.values.__getitem__(key)

    def __setitem__(self, key, value):
        """Provide access directly to the underlying value dictionary"""
        self._assert_key_is_member(key)
        self._assert_property_type(key, value)

        return self.values.__setitem__(key, value)

    def __delitem__(self, _):
        raise TypeError("Deleting entries from an EIP712Struct is not allowed.")

    def __eq__(self, other):
        if not other:
            # Null check
            return False
        if self is other:
            # Check identity
            return True
        if not isinstance(other, EIP712Struct):
            # Check class
            return False
        # Our structs are considered equal if their type signature and encoded value signature match.
        # E.g., like computing signable bytes but without a domain separator
        return (
            self.encode_type() == other.encode_type()
            and self.encode_value() == other.encode_value()
        )

    def __hash__(self):
        value_hashes = [hash(k) ^ hash(v) for k, v in self.values.items()]
        return functools.reduce(operator.xor, value_hashes, hash(self.type_name))


class StructTuple(NamedTuple):
    message: EIP712Struct
    domain: EIP712Struct


class BytesJSONEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, bytes):
            return to_hex(o)
        else:
            return super(BytesJSONEncoder, self).default(o)


def make_domain(
    name=None, version=None, chainId=None, verifyingContract=None, salt=None
):
    """Helper method to create the standard EIP712Domain struct for you.

    Per the standard, if a value is not used then the parameter is omitted from the struct entirely.
    """

    if all(i is None for i in [name, version, chainId, verifyingContract, salt]):
        raise ValueError("At least one argument must be given.")

    class EIP712Domain(EIP712Struct):
        pass

    kwargs = dict()
    if name is not None:
        EIP712Domain.name = String()
        kwargs["name"] = str(name)
    if version is not None:
        EIP712Domain.version = String()
        kwargs["version"] = str(version)
    if chainId is not None:
        EIP712Domain.chainId = Uint(256)
        kwargs["chainId"] = int(chainId)
    if verifyingContract is not None:
        EIP712Domain.verifyingContract = Address()
        kwargs["verifyingContract"] = verifyingContract
    if salt is not None:
        EIP712Domain.salt = Bytes(32)
        kwargs["salt"] = salt

    return EIP712Domain(**kwargs)
