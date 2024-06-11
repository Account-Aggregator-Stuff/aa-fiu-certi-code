### FIU/TSP Certification Module
This repository can be used to obtain FIU certification, which is required to use the Account Aggregator (AA) Framework API Specification as per the Sahamati Guidelines for AA and FIU. 

It will help you pass all the [test cases](https://github.com/Sahamati/certification-framework/blob/main/certification-scenarios/fiu.md) which is required to ensure adherence to technical standards in the AA ecosystem as per [v1.1.2](https://api.rebit.org.in/viewSpec/AA_1_1_2.yaml). There are ~70 Test Cases that need to be cleared.
 
Each test case is a combination of a request to AA (mock server) and a response. For each test case, there are checks (in request/response) and different types of requests to be made to different APIs or receive notifications and check for details in notifications received.

### How to Use the Module
1. The FIU can clone the repo. Host a PostgreSQL database and add its credentials in ".env" file.
2. Insert FIU details (client ID, RSA keys, token) and AA details (AA name, URL) in the Database.
3. Run the server(Django) along with DB credentials in the environment (can check Dockerfile for the same)
4. Use Postman (or any other client) to hit the APIs one by one as required for certification. (for consent/data request you will need to create a mock consent/data request)
5. The server needs to be hosted with access to the outside world as since URL needs to be provided to Sahamati so that AA can hit the URL to send notifications.
6. For JWS signing, the repo assumes an AWS lambda has been hosted but the team can write their own for JWS signature generation/verification if needed.

For obtaining the encryption/decryption keys, please follow the steps mentioned here in details: https://saafe.gitbook.io/docs/central-registry/create-fiu-entity

If you need assistance with the certification process, or encounter any technical issues while setting up or running the code, please don't hesitate to contact us for support.

#### Contact

Ritika Agarwal (agarwalritika101@gmail.com)

Lohit Marodia (lohitmarodia@gmail.com)
