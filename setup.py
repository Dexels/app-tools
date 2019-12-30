import setuptools

setuptools.setup(
    name="App tools",
    version="0.0.1",
    description="App tools",
    author="Dexelonian",
    author_email="info@dexels.com",
    packages=setuptools.find_packages(exclude=["test"]),
    python_requires=">=3.7",
    entry_points="""
    [console_scripts]
    app-entity=apptools.entity.cli:main
    """,
)