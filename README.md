# Assignment on AWS Infrastructure Automation

### Overview: 
Develop a system that automatically manages the lifecycle of a web application hosted on  EC2 instances, monitors its health, and reacts to changes in traffic by scaling resources.Furthermore, administrators receive notifications regarding the infrastructure's health and scaling events. 
#### Detailed Breakdown: 
1. Web Application Deployment: 
   - Use `boto3` to: 
   - Create an S3 bucket to store your web application's static files. 
   - Launch an EC2 instance and configure it as a web server (e.g., Apache, Nginx).  - Deploy the web application onto the EC2 instance. 
2. Load Balancing with ELB: 
   - Deploy an Application Load Balancer (ALB) using `boto3`. 
   - Register the EC2 instance(s) with the ALB. 
3. Auto Scaling Group (ASG) Configuration: 
   - Using `boto3`, create an ASG with the deployed EC2 instance as a template. 
   - Configure scaling policies to scale in/out based on metrics like CPU utilization or network traffic. 
4. SNS Notifications: 
   - Set up different SNS topics for different alerts (e.g., health issues, scaling events, high traffic). 
   - Integrate SNS with Lambda so that administrators receive SMS or email notifications. 
5. Infrastructure Automation: 
   - Create a single script using `boto3` that: 
   - Deploys the entire infrastructure. 
   - Updates any component as required. 
   - Tears down everything when the application is no longer needed. 
6. Optional Enhancement – Dynamic Content Handling: 
   - Store user-generated content or uploads on S3. 
   - When a user uploads content to the web application, it gets temporarily stored on the  EC2 instance. A background process (or another Lambda function) can move this to the S3  bucket and update the application's database to point to the content's new location on S3. 
#### Objectives: 
- Gain a comprehensive understanding of key AWS services and their integration.
- Understand the lifecycle of a dynamic web application and its infrastructure.
 
### Prerequisites
Prepare the development setup as follows:

   - Python 3.7 or higher installed.
     
   - Boto3 library installed (pip install boto3).
     ```bash
     pip3 install boto3
     ```
   - Configure AWS permissions via CLI command aws configure
     ```bash
      AWS Access Key ID [****************PC6D]: 
      AWS Secret Access Key [****************mBt6]: 
      Default region name [ap-northeast-2]: 
      Default output format [json]: json
     ```
