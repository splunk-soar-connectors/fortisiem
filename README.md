[comment]: # "Auto-generated SOAR connector documentation"
# FortiSIEM

Publisher: Armature Systems  
Connector Version: 1\.0\.0  
Product Vendor: Fortinet  
Product Name: FortiSIEM  
Product Version Supported (regex): "\.\*"  
Minimum Product Version: 4\.0\.1068  

This app implements powerful security, performance, compliance, information and event management\. It provides rapid detection and remediation of security events


Replace this text in the app's **readme.html** to contain more detailed information


### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a FortiSIEM asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**server** |  required  | string | IP/Hostname
**organization** |  required  | string | Organization
**username** |  required  | string | Username
**password** |  required  | password | Password
**verifyServerCert** |  optional  | boolean | Require server certificate verification
**incidentCategories** |  optional  | string | Incident Categories \(Comma separated\. Leave blank to get all incidents\)
**timeWindow** |  optional  | numeric | Time Window \(In minutes\. Default value is 2 hours\)
**minimumSeverity** |  required  | numeric | Minimum Event Severity \(Set to 0 to get all events\)

### Supported Actions  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration  
[on poll](#action-on-poll) - Callback action for the on\_poll ingest functionality  

## action: 'test connectivity'
Validate the asset configuration for connectivity using supplied configuration

Type: **test**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'on poll'
Callback action for the on\_poll ingest functionality

Type: **ingest**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**container\_id** |  optional  | Container IDs to limit the ingestion to | string | 
**start\_time** |  optional  | Start of time range, in epoch time \(milliseconds\) | numeric | 
**end\_time** |  optional  | End of time range, in epoch time \(milliseconds\) | numeric | 
**container\_count** |  optional  | Maximum number of container records to query for | numeric | 
**artifact\_count** |  optional  | Maximum number of artifact records to query for | numeric | 

#### Action Output
No Output