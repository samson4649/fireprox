

class FireProxAuthException(Exception): 
    """
    Exception for incorrect FireProx authentication.
    """
    pass  

class FireProxConfigException(Exception): 
    """
    Exception for incorrect FireProx configuration
    """
    pass

class FireProxAPIGWNotFound(Exception): 
    """
    Exception for invalid AWS API Gateway ID
    """
    pass

