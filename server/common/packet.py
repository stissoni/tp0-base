class Packet:
    def __init__(
        self,
        request_type,
        result,
        agency=None,
        first_name=None,
        last_name=None,
        doc=None,
        birthdate=None,
        bet_num=None,
    ):
        self.type = request_type
        self.result = result
        self.agency = agency
        self.first_name = first_name
        self.last_name = last_name
        self.doc = doc
        self.birthdate = birthdate
        self.bet_num = bet_num

    def serialize(self):
        serialization = f"{self.type},{self.result},{self.agency},{self.first_name},{self.last_name},{self.doc},{self.birthdate},{self.bet_num}\n"
        serialization_bytes = serialization.encode("utf-8")
        serialization_len = len(serialization_bytes)
        serialization_len_bytes = serialization_len.to_bytes(4, byteorder="big")
        return serialization_len_bytes + serialization_bytes

    @staticmethod
    def deserialize(serialization_bytes):
        serialization_str = serialization_bytes.decode("utf-8")
        serialization_list = serialization_str.split(",")
        return Packet(
            serialization_list[0],
            serialization_list[1],
            serialization_list[2],
            serialization_list[3],
            serialization_list[4],
            serialization_list[5],
            serialization_list[6],
            serialization_list[7],
        )
