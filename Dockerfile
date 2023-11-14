FROM mcr.microsoft.com/azure-cli
RUN pip install azure-mgmt-network azure-identity
WORKDIR /vnt