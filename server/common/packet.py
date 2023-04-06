class Packet:
    def __init__(
        self, type, result, agency, bet, first_name, last_name, doc, birthdate
    ):
        self.type = type
        self.result = result
        self.agency = agency
        self.first_name = first_name
        self.last_name = last_name
        self.doc = doc
        self.birthdate = birthdate
        self.bet = bet
