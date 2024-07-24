import boto3
import os
from botocore.exceptions import ClientError
import time
import ipaddress
import json
import zipfile

##### constants configuration parameters #####
SNS_TOPICS = {
    'health_issues': 'SONAL-Trigger-Health-Issues',
    'scaling_events': 'SONAL-Trigger-Scaling-Events',
    'high_traffic': 'SONAL-Trigger-High-Traffic'
}
IAM_ROLE_ARN = 'arn:aws:iam::975050024946:role/lambda-execution-role'
sg_id = 'sg-04f875fabed5e4e75' # SG launch wizard 4 
image_name = "ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-20240411"
subnet_id = 'subnet-07293e6abb2cf2426'
vpc_id = 'vpc-0f22c13329dc40837'
key_pair_name = 'MERN-SONAL'
server_name = 'sonal-test-server'
target_group_name= 'sonal-target-group'
lb_name='sonal-load-balancer'
bucket_name = 'sonal-bucket'
subnet_ids = ['subnet-0dc085f68a4254e66','subnet-05c5c244dc8e4409a','subnet-07293e6abb2cf2426','subnet-022c9b6354b90eb1a']
ami_name='sonal-ami-2'
autoscalingName="sonal-auto-scale"
policyName="sonal-policy"
launch_configuration_name="sonal-launch-configuration"
LAMBDA_NOTIFICATION_NAME = 'sonal-notification-handler'
bucket_name = 'sonal-bucket'
ami_id = ""
sns_topic_arn = ""


def create_bucket_if_not_exists(s3, bucket_name, region):
    try:
        location = {'LocationConstraint': region}
        response = s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration=location)
        if response["ResponseMetadata"]:
            print(f"Bucket created successfully: {response['Location']}")
        print(f'Bucket {bucket_name} created successfully')

    except s3.exceptions.BucketAlreadyExists as e:
        print(f'Bucket {bucket_name} already exists')
    except s3.exceptions.BucketAlreadyOwnedByYou as e:
        print(f'Bucket {bucket_name} already owned by you')
    except ClientError as e:
        print(f'Error creating bucket: {e}')
        return False

    return True

def upload_or_update_object(s3, bucket_name, file_path, object_key):
    try:
        s3.upload_file(file_path, bucket_name, object_key)
        print(f'File {file_path} uploaded to {bucket_name}/{object_key}')
    except FileNotFoundError:
        print(f'The file {file_path} was not found')
    except ClientError as e:
        print(f'Error uploading file: {e}')


def get_subnet_ids_for_vpc(ec2_client,vpc_id):
    subnet_ids = []
    response = ec2_client.describe_subnets(
        Filters=[
            {
                'Name': 'vpc-id',
                'Values': [vpc_id]
            }
        ]
    )
    for subnet in response["Subnets"]:
        subnet_ids.append(subnet['SubnetId'])
    return subnet_ids


def check_ec2_instance(ec2_client, servername):

    try:
        response = ec2_client.describe_instances(
            Filters=[
                {'Name': 'tag:Name', 'Values': [servername]},
                {'Name': 'instance-state-name', 'Values': ['running']}
            ]
        )

        if 'Reservations' in response:
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    print(f"{servername} Instance Already Present, Instance ID: {instance['InstanceId']}")
                    return instance['InstanceId']
        else:
            return None
    except ClientError as e:
        print(f"An error occurred: {e}")

def check_if_ami_exists(ec2_client, ami_name):
    try:
        existing_amis = ec2_client.describe_images(Filters=[{'Name': 'name', 'Values': [ami_name]}])
        if existing_amis['Images']:
            print(f"AMI with name '{ami_name}' already exists.")
            return existing_amis['Images'][0]['ImageId']
        else:
            return None
    except ClientError as e:
        print(f"An error occurred: {e}")
        return None
    
def create_ami(ec2_client, instance_id, ami_name):
    try:
        response = ec2_client.create_image(
            InstanceId=instance_id,
            Name=ami_name,
            Description='sonal ami',
            NoReboot=True
        )
        ami_id = response['ImageId']
        print(f"AMI {ami_id} created from instance {instance_id}")
        return ami_id
    except ClientError as e:
        print(f"An error occurred: {e}")
        return None
    

def create_ec2_instance(ec2_client,key_pair_name,sg_id,ami_image_id,user_data_script,subnet_id,servername):
    try:
        instance_response = ec2_client.run_instances(
            ImageId=ami_image_id,
            InstanceType='t2.micro',
            KeyName=key_pair_name,
            MinCount=1,
            MaxCount=1,
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {
                            'Key': 'Name',
                            'Value': servername
                        }
                    ]
                }
            ],
            SubnetId=subnet_id,
            SecurityGroupIds=[sg_id],
            UserData=user_data_script
        )
        if 'Instances' in instance_response:
            for instance in instance_response['Instances']:
                for tag in instance['Tags']:
                    if tag['Key'] == 'Name' and tag['Value'] == servername:
                        instance_id = instance['InstanceId']
                        break
            return instance_id
        else:
            return None
    except ClientError as e:
        print(f"An error occurred: {e}")

def check_existing_target_group(elbv2_client, target_group_name):
    try:
        response = elbv2_client.describe_target_groups()
        if response['TargetGroups']:
            for target_group in response['TargetGroups']:
                if target_group['TargetGroupName'] == target_group_name:
                    target_group_arn = target_group['TargetGroupArn']
                    return target_group_arn
        else:
            return None
    except ClientError as e:
        print(f"An error occurred: {e}")
        return None

def create_target_group_with_instances(elbv2_client, target_group_name, vpc_id, protocol, port, instances):
    try:
        existing_target_group_arn = check_existing_target_group(elbv2_client, target_group_name)
        if existing_target_group_arn:
            print(f"Target group {target_group_name} already exists with ARN: {existing_target_group_arn}")
            return existing_target_group_arn
        else:
            print("Target group with desired name is not present, Creating.....")
        
        # Create new target group if it doesn't exist
        response = elbv2_client.create_target_group(
            Name=target_group_name,
            Protocol=protocol,
            Port=port,
            VpcId=vpc_id,
            TargetType='instance',
            HealthCheckProtocol=protocol,
            HealthCheckPort=str(port),
            HealthCheckPath='/',
            HealthCheckIntervalSeconds=30,
            HealthCheckTimeoutSeconds=10,
            HealthyThresholdCount=3,
            UnhealthyThresholdCount=3
        )
        target_group_arn = response['TargetGroups'][0]['TargetGroupArn']
        print(f"Target group {target_group_name} created with ARN: {target_group_arn}")
        
        # Register instances with the target group
        if instances:
            for instance in instances:
                elbv2_client.register_targets(
                    TargetGroupArn=target_group_arn,
                    Targets=[
                        {
                            'Id': instance
                        }
                    ]
                )
                print(f"Instance {instance} registered with target group {target_group_name}")
        
        return target_group_arn
    except ClientError as e:
        print(f"An error occurred: {e}")
        return None


def check_load_balancer_exists(elb_client, lb_name):
    try:
        response = elb_client.describe_load_balancers(
            Names=[lb_name]
        )
        if response['LoadBalancers']:
            return response['LoadBalancers'][0]['LoadBalancerArn']
        else:
            return None
    except ClientError as e:
        if e.response['Error']['Code'] == 'LoadBalancerNotFound':
            print(f"Load balancer '{lb_name}' not found.")
        else:
            print(f"An error occurred: {e}")
        return None
    
def create_load_balancer(elb_client, lb_name, subnet_id, sg_id):
    try:
        response = elb_client.create_load_balancer(
            Name=lb_name,
            Subnets=subnet_id, 
            SecurityGroups=[sg_id],
            Scheme='internet-facing',
            Type='application',
            IpAddressType='ipv4'
        )
        if response['LoadBalancers']:
            return response['LoadBalancers'][0]['LoadBalancerArn']
        else:
            return None
    except ClientError as e:
        print(f"An error occurred while creating load balancer: {e}")
        return None


def check_listener_exists(elb_client, load_balancer_arn):
    try:
        response = elb_client.describe_listeners(LoadBalancerArn=load_balancer_arn)
        if response['Listeners']:
            return response['Listeners'][0]['ListenerArn']
        else:
            return None
    except ClientError as e:
        print(f"An error occurred: {e}")
        return None
    
def create_listener(elb_client, load_balancer_arn, target_group_arn):
    try:
        response = elb_client.create_listener(
            LoadBalancerArn=load_balancer_arn,
            Protocol='HTTP',
            Port=80,
            DefaultActions=[
                {
                    'Type': 'forward',
                    'TargetGroupArn': target_group_arn
                }
            ]
        )
        if response['Listeners']:
            return response['Listeners'][0]['ListenerArn']
        else:
            return None
    except ClientError as e:
        print(f"An error occurred: {e}")
        return None

def check_launch_configuration(autoscaling, launch_configuration_name):
    response = autoscaling.describe_launch_configurations(
        LaunchConfigurationNames=[launch_configuration_name]
    )
    # print (response)
    if response['LaunchConfigurations']:
        for LaunchConfiguration in response['LaunchConfigurations']:
            if LaunchConfiguration and LaunchConfiguration["LaunchConfigurationName"] == launch_configuration_name:
                print(f"Launch configuration '{launch_configuration_name}' already exists.")
                return True
    return False

def create_launch_configuration(autoscaling, launch_configuration_name, ami_id, key_pair_name, sg_id, user_data_script):
    try:
        response = autoscaling.create_launch_configuration(
            LaunchConfigurationName=launch_configuration_name,
            ImageId=ami_id,
            InstanceType='t2.micro',
            KeyName=key_pair_name,
            SecurityGroups=[sg_id], 
            UserData=user_data_script
        )
        print('Created launch configuration')
        return response
    except ClientError as e:
        print(f"An error occurred: {e}")
        return None

def check_autoscaling(autoscaling, autoscalingName):
    response = autoscaling.describe_auto_scaling_groups(
        AutoScalingGroupNames=[autoscalingName]
        )
    if response['AutoScalingGroups']:
        for AutoScalingGroup in response['AutoScalingGroups']:
            if AutoScalingGroup and AutoScalingGroup["AutoScalingGroupName"] == autoscalingName:
                print(f"Auto scaling group '{autoscalingName}' already exists.")
                return True
    print("Auto scaling not found..")
    return False
        
def create_autoscaling(autoscaling, target_group_arn, autoscalingName, launch_configuration_name, subnet_ids):
    try:    
        vpc_zone_identifier = ','.join(subnet_ids)
        response = autoscaling.create_auto_scaling_group(
            AutoScalingGroupName=autoscalingName,
            LaunchConfigurationName=launch_configuration_name,
            MinSize=1,
            MaxSize=3,
            DesiredCapacity=1,
            VPCZoneIdentifier=vpc_zone_identifier,
            TargetGroupARNs=[target_group_arn],
            Tags=[
                {
                    'ResourceId': autoscalingName,
                    'ResourceType': 'auto-scaling-group',
                    'Key': 'Name',
                    'Value': autoscalingName,
                    'PropagateAtLaunch': True
                },
            ]
        )
        print(response)

        print('Created auto scaling group')

        return response
    except Exception as e:
        return None

def check_scaling_policy_existence(autoscaling,asg_name, policy_name):
    try:
        response = autoscaling.describe_policies(
            AutoScalingGroupName=asg_name,
            PolicyNames=[policy_name]
        )
        if response['ScalingPolicies']:
            for policy in response['ScalingPolicies']:
                if policy and policy["PolicyName"] == policy_name:
                    return True
    except Exception as e:
        if e.response['Error']['Code'] == 'ValidationError':
            print(f"Group '{asg_name}' not found")
            return False
        else:
            print(f"An error occurred: {e}")
            return False
    
def create_scaling_policy(autoscaling, autoscalingName, policyName):
    try:
        response = autoscaling.put_scaling_policy(
                AutoScalingGroupName=autoscalingName,
                PolicyName=policyName,
                PolicyType='TargetTrackingScaling',
                TargetTrackingConfiguration={
                    'PredefinedMetricSpecification': {
                        'PredefinedMetricType': 'ASGAverageCPUUtilization'
                    },
                    'TargetValue': 50.0  
                }
            )
        return response 
    except:
        return None
    
def get_ami_image_id_from_image_name(ec2_client,image_name):
    response = ec2_client.describe_images(
        Filters=[
            {
                'Name': 'name',
                'Values': [image_name]
            }
        ]
    )

    # Extract the image ID from the response
    if response['Images']:
        ami_id = response['Images'][0]['ImageId']
        print(f"AMI ID: {ami_id}")
        return ami_id
    else:
        print(f"No AMI found with name: {image_name}")
        return None
    
def create_sns_topic(sns, name):
    try:
        response = sns.create_topic(Name=name)
        print("SNS Topic created:", response['TopicArn'])
        return response['TopicArn']
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    
def create_lambda_function(lambda_client,name, zip_file, handler):
    try:
        with open(zip_file, 'rb') as f:
            code = f.read()
        response = lambda_client.create_function(
            FunctionName=name,
            Runtime='python3.8',
            Role=IAM_ROLE_ARN,
            Handler=handler,
            Code={'ZipFile': code},
            Description=f'Lambda function for {name}',
            Timeout=60,
            MemorySize=128,
            Publish=True
        )
        print("Lambda Function created:", response['FunctionArn'])
        return response['FunctionArn']
    except Exception as e:
        print(f"Error creating Lambda function {name}:", e)

def subscribe_lambda_to_sns(sns,topic_arn, lambda_arn):
    try:
        response = sns.subscribe(
            TopicArn=topic_arn,
            Protocol='lambda',
            Endpoint=lambda_arn
        )
        print("Lambda subscribed to SNS Topic:", response)
        return response
    except Exception as e:
        print(f"Error creating Lambda function:", e)


def subscribe_email_to_sns(sns,topic_arn, lambda_arn):
    response = sns.subscribe(
    TopicArn=topic_arn,
    Protocol='email',
    Endpoint="28himanshu@gmail.com")


def write_and_zip_lambda(name, code):
    with open(f'{name}.py', 'w') as f:
        f.write(code)
    with zipfile.ZipFile(f'{name}.zip', 'w') as z:
        z.write(f'{name}.py')
    os.remove(f'{name}.py')

### lamba function code 

lambda_notification_code = '''
import json
import boto3

def lambda_handler(event, context):
    sns_message = event['Records'][0]['Sns']['Message']
    print("Received SNS message:", sns_message)
    
    # Initialize the SNS client
    sns_client = boto3.client('sns')
    
    # Define the recipient's phone number
    recipient_phone_number = '+918860020619'  # Replace with actual phone number
    
    # Logic to handle different types of notifications
    if 'health issue' in sns_message:
        # Handle health issue notification
        sns_client.publish(
            PhoneNumber=recipient_phone_number,
            Message=f"Health Issue Alert: {sns_message}"
        )
    elif 'scaling event' in sns_message:
        # Handle scaling event notification
        sns_client.publish(
            PhoneNumber=recipient_phone_number,
            Message=f"Scaling Event Alert: {sns_message}"
        )
    elif 'high traffic' in sns_message:
        # Handle high traffic notification
        sns_client.publish(
            PhoneNumber=recipient_phone_number,
            Message=f"High Traffic Alert: {sns_message}"
        )
    else:
        # Handle general notifications
        sns_client.publish(
            PhoneNumber=recipient_phone_number,
            Message=f"General Alert: {sns_message}"
        )
'''
write_and_zip_lambda('lambda_function', lambda_notification_code)

def create_resources():
    try:
        ec2_client = boto3.client('ec2' , region_name="ap-northeast-2")
        elbv2_client = boto3.client('elbv2', region_name="ap-northeast-2")
        autoscaling = boto3.client('autoscaling', region_name="ap-northeast-2")
        sns = boto3.client('sns',region_name="ap-northeast-2")
        s3 = boto3.client('s3', region_name="ap-northeast-2")
        lambda_client = boto3.client('lambda', region_name="ap-northeast-2")

        with open('./startup_script.sh', 'r') as userdata_file:
            user_data_script = userdata_file.read()

        ami_image_id = get_ami_image_id_from_image_name(ec2_client,image_name)


        if create_bucket_if_not_exists(s3, bucket_name, region="ap-northeast-2"):
            upload_or_update_object(s3, bucket_name, "index.html", "index.html")


        instance_id = check_ec2_instance(ec2_client, servername=server_name)
        if instance_id is None:
            print("Primary server instance not found. Creating one..")

            instance_id = create_ec2_instance(ec2_client, key_pair_name, sg_id, ami_image_id, user_data_script, subnet_id, servername='sonal-test-server')
            if instance_id is not None:
                print(f"sonal-test-server created: {instance_id}")
                print("Waiting for the instance to be up and UserData to execute...")
                time.sleep(420)
                ami_id = create_ami(ec2_client, instance_id, ami_name)
                waiter = ec2_client.get_waiter('image_available')
                print("Waiting for AMI to become available...")
                waiter.wait(ImageIds=[ami_id])
                print(f"AMI {ami_id} is now available.")
        else:
            ami_id = check_if_ami_exists(ec2_client, ami_name)
            if ami_id is None:
                ami_id = create_ami(ec2_client, instance_id, ami_name)
                waiter = ec2_client.get_waiter('image_available')
                print("Waiting for AMI to become available...")
                waiter.wait(ImageIds=[ami_id])
                print(f"AMI {ami_id} is now available.")


        target_group_arn = create_target_group_with_instances(elbv2_client, target_group_name, vpc_id, 'HTTP', 80, [instance_id])
        if target_group_arn is None:
            print("Failed to create target group.")

        load_balancing_arn = check_load_balancer_exists(elbv2_client, lb_name)
        if load_balancing_arn is None:
            load_balancing_arn = create_load_balancer(elbv2_client, lb_name, subnet_ids, sg_id)

        if load_balancing_arn is not None:
            listener_arn = check_listener_exists(elbv2_client, load_balancing_arn)
            if listener_arn is None:
                listener_arn = create_listener(elbv2_client, load_balancing_arn, target_group_arn)
        else:
            print("Failed to create load balancer.")
        
        print(f"Load balancing ARN: {load_balancing_arn}")
        

        launch_config_exists = check_launch_configuration(autoscaling, launch_configuration_name)
        if not launch_config_exists:
            print("Creating launch configuration...")
            launch_configuration_arn = create_launch_configuration(autoscaling, launch_configuration_name, ami_id, key_pair_name, sg_id, user_data_script)
            if launch_configuration_arn is None or launch_configuration_arn["ResponseMetadata"]["HTTPStatusCode"] != 200:
                print("Failed to create launch configuration.")

        autoscaling_exists = check_autoscaling(autoscaling, autoscalingName)
        if not autoscaling_exists:
            subnets = get_subnet_ids_for_vpc(ec2_client,vpc_id)
            response_autoscaling = create_autoscaling(autoscaling, target_group_arn, autoscalingName, launch_configuration_name, subnets)
            if response_autoscaling is None:
                print("Failed to create autoscaling group.")

        sns_topic_arn = create_sns_topic(sns,SNS_TOPICS['scaling_events'])
        autoscaling.put_notification_configuration(
            AutoScalingGroupName=autoscalingName,
            TopicARN=sns_topic_arn,
            NotificationTypes=['autoscaling:EC2_INSTANCE_LAUNCH', 'autoscaling:EC2_INSTANCE_TERMINATE']
        )


        scaling_policy_exists = check_scaling_policy_existence(autoscaling, autoscalingName, policyName)
        if not scaling_policy_exists:
            response_scaling_policy = create_scaling_policy(autoscaling, autoscalingName, policyName)
            if response_scaling_policy is None:
                print("Failed to create scaling policy.")

        for topic_name in SNS_TOPICS.values():
            topic_arn = create_sns_topic(sns,topic_name)
            lambda_arn = create_lambda_function(lambda_client,LAMBDA_NOTIFICATION_NAME,'lambda_function.zip','lambda_function.lambda_handler')
            subscribe_lambda_to_sns(sns,topic_arn, lambda_arn)
            subscribe_email_to_sns(sns,topic_arn, lambda_arn)

    except ClientError as e:
        print(f"An error occurred: {e}")
##########################################################################################
### functions to handle delete resources ###
##########################################################################################
def delete_objects_in_bucket(s3, bucket_name):
    try:
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name)

        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    s3.delete_object(Bucket=bucket_name, Key=obj['Key'])
                    print(f'Deleted {obj["Key"]} from {bucket_name}')

        

    except Exception as e:
        if e.response['Error']['Code'] == 'NoSuchBucket':
            print(f"Bucket '{bucket_name}' not found")
        else:
            print(f"An error occurred: {e}")


def delete_bucket(s3, bucket_name):
    try:
        s3.delete_bucket(Bucket=bucket_name)
        print(f'Bucket {bucket_name} deleted successfully')

    except Exception as e:
        if e.response['Error']['Code'] == 'NoSuchBucket':
            print(f"Bucket '{bucket_name}' not found")
        else:
            print(f"An error occurred: {e}")


def delete_ec2_instance(ec2_client, instance_id):
    try:
        ec2_client.terminate_instances(InstanceIds=[instance_id])
        print(f"Terminated EC2 instance with ID: {instance_id}")
    except ClientError as e:
        print(f"Failed to terminate instance {instance_id}: {e}")

def remove_ami(ec2_client, ami_id):
    try:
        ec2_client.deregister_image(ImageId=ami_id)
        print(f"Deregistered AMI with ID: {ami_id}")
    except ClientError as e:
        print(f"Failed to deregister AMI {ami_id}: {e}")

def delete_load_balancer(elbv2_client, load_balancer_arn):
    try:
        elbv2_client.delete_load_balancer(LoadBalancerArn=load_balancer_arn)
        print(f"Deleted load balancer with ARN: {load_balancer_arn}")
    except ClientError as e:
        print(f"Failed to delete load balancer {load_balancer_arn}: {e}")

def delete_listener(elbv2_client, listener_arn):
    try:
        elbv2_client.delete_listener(ListenerArn=listener_arn)
        print(f"Deleted listener with ARN: {listener_arn}")
    except ClientError as e:
        print(f"Failed to delete listener {listener_arn}: {e}")

def delete_auto_scaling_group(autoscaling, autoscalingName):
    try:
        autoscaling.delete_auto_scaling_group(AutoScalingGroupName=autoscalingName, ForceDelete=True)
        print(f"Deleted auto scaling group: {autoscalingName}")
    except ClientError as e:
        print(f"Failed to delete auto scaling group {autoscalingName}: {e}")

def delete_scaling_policy(autoscaling, asg_name, policy_name):
    try:
        autoscaling.delete_policy(AutoScalingGroupName=asg_name, PolicyName=policy_name)
        print(f"Deleted scaling policy: {policy_name} for Auto Scaling Group: {asg_name}")
    except ClientError as e:
        print(f"Failed to delete scaling policy {policy_name} for Auto Scaling Group {asg_name}: {e}")

def delete_launch_configuration(autoscaling, launch_configuration_name):
    try:
        autoscaling.delete_launch_configuration(LaunchConfigurationName=launch_configuration_name)
        print(f"Deleted launch configuration: {launch_configuration_name}")
    except ClientError as e:
        print(f"Failed to delete launch configuration {launch_configuration_name}: {e}")

def delete_target_group(elbv2_client, target_group):
    try:
        elbv2_client.delete_target_group(TargetGroupArn=target_group)
        print(f"Deleted target group: {target_group}")
    except ClientError as  e:
        print(f"Failed to delete target group {target_group}: {e}")

def delete_sns_topics(sns_client):
    for topic_name in SNS_TOPICS.values():
        try:
            sns_client.delete_topic(sns_topic_arn)
            print(f"SNS Topic {topic_name} deleted.")
        except ClientError as e:
            print(f"Error deleting SNS Topic {topic_name}:", e)


def delete_resources():
    ec2_client = boto3.client('ec2')
    elbv2_client = boto3.client('elbv2')
    autoscaling = boto3.client('autoscaling')
    sns_client = boto3.client('sns')
    lambda_client = boto3.client('lambda')
    s3 = boto3.client('s3')


    instance_id = check_ec2_instance(ec2_client, servername=server_name)

    
    target_group = check_existing_target_group(elbv2_client, target_group_name)

    #subnets = get_subnet_ids_for_vpc(ec2_client, vpc_id)
    load_balancing_arn = check_load_balancer_exists(elbv2_client, lb_name)
    listener_arn = ""
    if load_balancing_arn:  
        listener_arn = check_listener_exists(elbv2_client, load_balancing_arn)
        
    launch_config_exists = check_launch_configuration(autoscaling, launch_configuration_name)
    autoscaling_exists = check_autoscaling(autoscaling, autoscalingName)
    scaling_policy_exists = check_scaling_policy_existence(autoscaling, autoscalingName, policyName)

    delete_objects_in_bucket(s3,bucket_name)

    delete_bucket(s3, bucket_name)
    
    if instance_id:
        delete_ec2_instance(ec2_client, instance_id)
    
    ami_id = check_if_ami_exists(ec2_client, ami_name)
    
    if ami_id:
        remove_ami(ec2_client, ami_id)

    
    if load_balancing_arn:
        delete_load_balancer(elbv2_client, load_balancing_arn)
    
    if listener_arn:
        delete_listener(elbv2_client, listener_arn)
    
    if autoscaling_exists:
        delete_auto_scaling_group(autoscaling, autoscalingName)
    
    if scaling_policy_exists:
        delete_scaling_policy(autoscaling, autoscalingName, policyName)
    
    if launch_config_exists:
        delete_launch_configuration(autoscaling, launch_configuration_name)
    
    if target_group:
        delete_target_group(elbv2_client, target_group)

    if sns_topic_arn != "":
        delete_sns_topics(sns_client)

    try:
        lambda_client.delete_function(FunctionName=LAMBDA_NOTIFICATION_NAME)
        print("Lambda Notification Function deleted.")
    except Exception as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"Lambda function '{LAMBDA_NOTIFICATION_NAME}' not found")
        else:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    action = input("Enter action: create or delete: ").strip().lower()
    if action == "create":
        create_resources()
    elif action == "delete":
        delete_resources()
    else:
        print("Invalid action. Please enter create or delete.")
