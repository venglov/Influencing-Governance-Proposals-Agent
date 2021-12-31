class Web3Mock:
    def __init__(self, checkpoints):
        self.eth = EthMock(checkpoints)


class EthMock:
    def __init__(self, checkpoints):
        self.contract = ContractMock(checkpoints)


class ContractMock:
    def __init__(self, checkpoints):
        self.functions = FunctionsMock(checkpoints)

    def __call__(self, address, *args, **kwargs):
        return self


class FunctionsMock:
    def __init__(self, checkpoints):
        self.checkpoints_list = checkpoints
        self.return_value = None

    def checkpoints(self, account, index):
        self.return_value = self.checkpoints_list[index]
        return self

    def numCheckpoints(self, *_, **__):
        self.return_value = len(self.checkpoints_list)
        return self

    def call(self, *_, **__):
        return self.return_value
