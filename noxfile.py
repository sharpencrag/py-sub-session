import nox


@nox.session(python=["3.7"])
def tests(session):
    session.install(".")
    session.run("python", "-m", "unittest", "discover", "-s", "tests")
