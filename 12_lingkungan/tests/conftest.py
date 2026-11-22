import os


def pytest_addoption(parser):
    d = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "10_runner", "DQN_Akselerasi vertikal"))
    parser.addoption("--dir_dika", default=d, help="folder DQN_Akselerasi vertikal (kode + model + Yolo Dika)")
