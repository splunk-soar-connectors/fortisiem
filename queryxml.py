from xml.dom.minidom import Document


def create_null_discovery_request():
    """
    <?xml version="1.0" ?>
    <discoverRequest>
        <type>SmartScan</type>
    </discoverRequest>
    """
    doc = Document()
    discoverRequest = doc.createElement("discoverRequest")
    doc.appendChild(discoverRequest)

    type = doc.createElement("type")
    discoverRequest.appendChild(type)
    typeText = doc.createTextNode("SmartScan")
    type.appendChild(typeText)

    return doc.toxml()


def create_query_xml(incidentCategories, timeWindow, minimumSeverity):
    """
    <?xml version="1.0" ?>
    <Reports>
        <Report group="report" id="All Incidents">
            <Name/>
            <CustomerScope groupByEachCustomer="true">
                <Include all="true"/>
                <Exclude/>
            </CustomerScope>
            <description/>
            <SelectClause numEntries="All">
                <AttrList/>
            </SelectClause>
            <ReportInterval>
                <Window unit="Minute" val=timeWindow/>
            </ReportInterval>
            <PatternClause window="3600">
                <SubPattern displayName="Incidents" name="Incidents">
                <SingleEvtConstr>phEventCategory=1 AND (phIncidentCategory = 'Category1' OR phIncidentCategory = 'Category2') AND eventSeverity >= 3</SingleEvtConstr>
                </SubPattern>
            </PatternClause>
            <RelevantFilterAttr/>
        </Report>
    </Reports>
    """

    doc = Document()
    reports = doc.createElement("Reports")
    doc.appendChild(reports)

    report = doc.createElement("Report")
    report.setAttribute("id", "All Incidents")
    report.setAttribute("group", "report")
    reports.appendChild(report)

    name = doc.createElement("Name")
    report.appendChild(name)
    doc.createTextNode("All Incidents")

    custScope = doc.createElement("CustomerScope")
    custScope.setAttribute("groupByEachCustomer", "true")
    report.appendChild(custScope)

    include = doc.createElement("Include")
    include.setAttribute("all", "true")
    custScope.appendChild(include)
    exclude = doc.createElement("Exclude")
    custScope.appendChild(exclude)

    description = doc.createElement("description")
    report.appendChild(description)

    select = doc.createElement("SelectClause")
    select.setAttribute("numEntries", "All")
    report.appendChild(select)
    attrList = doc.createElement("AttrList")
    select.appendChild(attrList)

    # Set the report interval to the time window from app config
    reportInterval = doc.createElement("ReportInterval")
    report.appendChild(reportInterval)
    window = doc.createElement("Window")
    window.setAttribute("unit", "Minute")
    window.setAttribute("val", str(timeWindow))
    reportInterval.appendChild(window)

    pattern = doc.createElement("PatternClause")
    pattern.setAttribute("window", "3600")
    report.appendChild(pattern)
    subPattern = doc.createElement("SubPattern")
    subPattern.setAttribute("displayName", "Incidents")
    subPattern.setAttribute("name", "Incidents")
    pattern.appendChild(subPattern)
    single = doc.createElement("SingleEvtConstr")
    subPattern.appendChild(single)

    # Filter the events returned by the query by event category and severity
    SingleEvtConstr = "phEventCategory=1 AND eventSeverity>={0}".format(minimumSeverity)

    # Turn list of incident categories into list of constraints and add to filter
    if incidentCategories:
        incidentCategoriesList = incidentCategories.split(',')
        newIncidentCategoriesList = ["phIncidentCategory='{0}'".format(i) for i in incidentCategoriesList]
        incidentCategoryConstr = " OR ".join(newIncidentCategoriesList)
        SingleEvtConstr = "{0} AND ({1})".format(SingleEvtConstr, incidentCategoryConstr)

    singleText = doc.createTextNode(SingleEvtConstr)
    single.appendChild(singleText)

    filter = doc.createElement("RelevantFilterAttr")
    report.appendChild(filter)

    return doc.toxml()


if __name__ == '__main__':

    print "create_null_discovery_request()"
    print "-------------------------------"
    print(create_null_discovery_request())
    print ""
    print "create_query_xml()"
    print "------------------"
    print ""
    print(create_query_xml("TestIncidentType,AnotherTestType,OneMoreIncidentType", 60, 7))
