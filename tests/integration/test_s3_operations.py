def test_s3_put_get(s3_client):
    bucket = "test-bucket"
    # some endpoints/regions require an explicit LocationConstraint
    region = getattr(s3_client.meta, "region_name", None) or "us-east-1"
    if region == "us-east-1":
        s3_client.create_bucket(Bucket=bucket)
    else:
        s3_client.create_bucket(Bucket=bucket, CreateBucketConfiguration={"LocationConstraint": region})
    s3_client.put_object(Bucket=bucket, Key="hello.txt", Body=b"hello world")
    res = s3_client.get_object(Bucket=bucket, Key="hello.txt")
    data = res["Body"].read()
    assert data == b"hello world"
