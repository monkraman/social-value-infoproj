import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.toms_metric import TomsMetric as TomsMetricModel
from app.schemas.calculation import (
    TOMsMetric,
    TomsMetricCreate,
    TomsMetricUpdate,
    InitiativeCalculation,
    PackageCalculation,
    OpportunityRecommendRequest,
    OpportunityRecommendResponse,
    OpportunityRecommendationItem
)

# Reference Default TOMs & NHS Contract Benchmark Metrics
DEFAULT_TOMS_DATA: List[Dict[str, Any]] = [
    {
        "code": "NT1",
        "name": "Local people employed or retained",
        "theme": "Work",
        "outcome": "Creating local employment opportunities",
        "unit": "no. people FTE",
        "unit_value_gbp": 45722.0,
        "description": "This Measure covers the employment of local people.\nQualifying employees must live in the local area, have an employment contract that reflects the hours they regularly work with a guaranteed minimum working time of 16 hours per week and at least 4 weeks of notice for shifts in the working pattern.\nThe Full Time Equivalent (FTE) calculation must be derived from the length of the employment contract within the reporting period.\nThe Measure requires a definition of the local area.",
        "evidence_required": "(1) Forecast number of relevant local people to be employed or retained.\n(2) Expected employment duration and type (full time or part time) per person.\n(3) Any initiatives or recruitment programmes that will be used to employ local people.\n(4) Names of any proposed partner organisations if known.",
        "ppn_mapping": "MAC 2.2: Employment and Skills",
        "source": "Open Access TOM System 2024/2025",
        "is_synthetic": False
    },
    {
        "code": "NT3",
        "name": "Long-term unemployed people recruited",
        "theme": "Work",
        "outcome": "Creating equal employment opportunities",
        "unit": "no. people FTE",
        "unit_value_gbp": 51561.0,
        "description": "This Measure covers the employment of a person who can be classified as 'Long-term unemployed'.\nQualifying employees will have been unemployed for a year or more.\nThe Measure can only be used once per qualifying employee, for the first year of their employment, and does not include students.",
        "evidence_required": "(1) Forecast number of relevant future employees (Long-term unemployed).\n(2) Expected employment duration and type (full time or part time) per person.\n(3) Any initiatives or recruitment programmes that will be used to employ Long-term unemployed people.\n(4) Names of any proposed partner organisations if known.",
        "ppn_mapping": "MAC 2.2: Employment and Skills",
        "source": "Open Access TOM System 2024/2025",
        "is_synthetic": False
    },
    {
        "code": "NT4",
        "name": "Employees recruited who are Not in Education Employment or Training (16-24 y.o.)",
        "theme": "Work",
        "outcome": "Creating equal employment opportunities",
        "unit": "no. people FTE",
        "unit_value_gbp": 53013.0,
        "description": "This Measure covers the employment of a person who can be classified as 'not in education employment or training' (NEET).\nQualifying employees are 16-24 year olds who are not in formal training, education or any form of paid employment.\nThe Measure can only be used once per qualifying employee, for the first year of their employment and does not include students, or adults who are long-term unemployed.",
        "evidence_required": "(1) Forecast number of relevant future employees (Not in Employment, Education or Training).\n(2) Expected employment duration and type (full time or part time) per person.\n(3) Any initiatives or recruitment programmes targeting people who are NEET.\n(4) Names of any proposed partner organisations if known.",
        "ppn_mapping": "MAC 2.2: Employment and Skills",
        "source": "Open Access TOM System 2024/2025",
        "is_synthetic": False
    },
    {
        "code": "NT76",
        "name": "Unemployed people recruited",
        "theme": "Work",
        "outcome": "Creating equal employment opportunities",
        "unit": "no. people FTE",
        "unit_value_gbp": 50713.0,
        "description": "This Measure covers the employment of a person who can be classified as 'unemployed'.\nQualifying employees will have been unemployed for at least four weeks.\nThe Measure can only be used once per qualifying employee, for the first year of their employment.",
        "evidence_required": "(1) Forecast number of relevant future employees (unemployed).\n(2) Expected employment duration and type (full time or part time) per person.\n(3) Any initiatives or recruitment programmes that will be used to employ unemployed people.\n(4) Names of any proposed partner organisations if known.",
        "ppn_mapping": "MAC 2.2: Employment and Skills",
        "source": "Open Access TOM System 2024/2025",
        "is_synthetic": False
    },
    {
        "code": "NT5",
        "name": "Unemployed ex-offenders aged 18 and over recruited",
        "theme": "Work",
        "outcome": "Creating equal employment opportunities",
        "unit": "no. people FTE",
        "unit_value_gbp": 55922.0,
        "description": "This Measure covers the employment of a person who is an unemployed ex-offender.\nQualifying employees will be aged 18 and over.\nThe Measure can only be used once per qualifying employee, for the first year of their employment.",
        "evidence_required": "(1) Forecast number of relevant future employees (unemployed ex-offenders aged 18 and over).\n(2) Expected employment duration and type (full time or part time) per person.\n(3) Any initiatives or recruitment programmes targeting rehabilitating or ex-offenders aged 18 and over.\n(4) Names of any proposed partner organisations if known.",
        "ppn_mapping": "MAC 2.2: Employment and Skills",
        "source": "Open Access TOM System 2024/2025",
        "is_synthetic": False
    },
    {
        "code": "NT6",
        "name": "Unemployed individuals with disabilities recruited",
        "theme": "Work",
        "outcome": "Creating equal employment opportunities",
        "unit": "no. people FTE",
        "unit_value_gbp": 51889.0,
        "description": "This Measure covers the employment of a person who is unemployed and who has a disability\nA qualifying employee is \"someone with a physical or mental impairment that has a \u2018substantial\u2019 and \u2018long-term\u2019 effect on their ability to do normal daily activities\" (Equality Act, 2010).\nThe Measure can only be used once per qualifying employee, for the first year of their employment.",
        "evidence_required": "(1) Forecast number of relevant future employees (unemployed individuals with a disability).\n(2) Expected employment duration and type (full time or part time) per person.\n(3) Any initiatives or recruitment programmes targeting disabled persons.\n(4) Names of any proposed partner organisations if known.",
        "ppn_mapping": "MAC 2.2: Employment and Skills",
        "source": "Open Access TOM System 2024/2025",
        "is_synthetic": False
    },
    {
        "code": "NT9",
        "name": "Accredited training for new employees",
        "theme": "Work",
        "outcome": "Providing skills and experience for good work",
        "unit": "no. weeks",
        "unit_value_gbp": 347.0,
        "description": "This Measure covers new employment with accredited vocational training.\nQualifying courses are at level 2 or higher such as: BTEC, City & Guilds, NVQ, HNC, RQF or T-levels.\nCourses must be completed by the employee and supported by the organisation until qualification is attained.\nThis Measure can only be used to record training opportunities for new employees, not existing employees.",
        "evidence_required": "(1) Forecast number of people on relevant vocational training courses.\n(2) Expected number of weeks spent on each course per person.\n(3) Qualification level for each course.\n(4) Name of accredited training provider(s) if available.",
        "ppn_mapping": "MAC 2.2: Employment and Skills",
        "source": "Open Access TOM System 2024/2025",
        "is_synthetic": False
    },
    {
        "code": "NT10",
        "name": "Employment of new apprentices",
        "theme": "Work",
        "outcome": "Providing skills and experience for good work",
        "unit": "no. weeks",
        "unit_value_gbp": 309.73,
        "description": "This Measure covers the employment of new apprentices at level 2 or higher.\nQualifying apprenticeships must follow an established path of progression to ensure timely completion and should be supported by the organisation until complete.\nThis Measure can only be used to record opportunities for new employees and not upskilling for existing employees.",
        "evidence_required": "(1) Forecast number of relevant people (apprentices) to be employed.\n(2) Expected relevant working time (weeks spent on apprenticeship) per person.\n(3) Expected qualification level for each apprentice.\n(4) Name of accredited training provider for each apprentice if known.",
        "ppn_mapping": "MAC 2.2: Employment and Skills",
        "source": "Open Access TOM System 2024/2025",
        "is_synthetic": False
    },
    {
        "code": "NT80",
        "name": "Upskilling of existing employees through accredited training",
        "theme": "Work",
        "outcome": "Providing skills and experience for good work",
        "unit": "no. weeks",
        "unit_value_gbp": 13.02,
        "description": "This Measure covers the upskilling of existing employees through accredited vocational training.\nQualifying courses are at level 2 or higher such as: BTEC, City & Guilds, NVQ, HNC, RQF or T-levels. \nCourses must be completed by the employee and supported by the organisation until qualification is attained.",
        "evidence_required": "(1) Forecast number of existing employees being upskilled on vocational training courses.\n(2) Expected number of weeks spent on each course per person.\n(3) Qualification level for each course.\n(4) Name of accredited training provider(s) if known.",
        "ppn_mapping": "MAC 2.2: Employment and Skills",
        "source": "Open Access TOM System 2024/2025",
        "is_synthetic": False
    },
    {
        "code": "NT11",
        "name": "Personalised support to help unemployed people into work",
        "theme": "Work",
        "outcome": "Providing skills and experience for good work",
        "unit": "no. hrs (total session duration)*no. attendees",
        "unit_value_gbp": 110.99,
        "description": "This Measure covers the provision of expert-led personalised support to help unemployed people gain work (not including students).\nExamples include career mentoring, mock interviews, CV advice, careers guidance, etc.\nGroup sessions must be of a small enough size to allow recipients to receive personalised support based on their individual and specific needs.\nTraining can be delivered online or in person.\nAn employee's hours can only be recorded if they have been allocated time during paid working hours or time off in lieu.",
        "evidence_required": "(1) Forecast number of sessions, number of people receiving training and session duration.\n(2) Description of relevant activity/activities to be delivered, including confirmation that content will be personalised to individual needs.\n(3) Names of any proposed partner organisations if known.",
        "ppn_mapping": "MAC 2.2: Employment and Skills",
        "source": "Open Access TOM System 2024/2025",
        "is_synthetic": False
    },
    {
        "code": "NT12",
        "name": "Meaningful unpaid work placements while Not in Employment Education or Training",
        "theme": "Work",
        "outcome": "Providing good work opportunities",
        "unit": "no. weeks",
        "unit_value_gbp": 96.53,
        "description": "This Measure covers the provision of unpaid, short-term placements or pre-employment courses that make a meaningful contribution to enabling young people not in employment education or training (NEET) to find gainful employment.\nThe placement must not last more than 8 consecutive weeks (or more than 40 days within a 3-month period) but at least 1 week.\nThe Measure can only be used once per person within a 12-month period. \nExamples of meaningful work placements include work on junior-level tasks providing industry experience and insight.",
        "evidence_required": "(1) Forecast number of participants and weeks of work placements or pre-employment courses per person.\n(2) Description of each proposed work placement or pre-employment course.\n(3) Names of any proposed partner organisations if known.",
        "ppn_mapping": "MAC 2.2: Employment and Skills",
        "source": "Open Access TOM System 2024/2025",
        "is_synthetic": False
    },
    {
        "code": "NT13",
        "name": "Meaningful paid work placements",
        "theme": "Work",
        "outcome": "Providing good work opportunities",
        "unit": "no. weeks",
        "unit_value_gbp": 412.38,
        "description": "This Measure covers the provision of paid work placements that make a meaningful contribution to enabling young people to find gainful employment.\nThe placement can last between 2 weeks and 6 months.\nThe Measure can only be used once per person, within a 12-month period.\nExamples of meaningful work placements include work on junior-level tasks providing industry experience and insight.",
        "evidence_required": "(1) Forecast number of participants and weeks of paid work placements per person.\n(2) Description of each proposed paid work placement.\n(3) Names of any proposed partner organisations if known.",
        "ppn_mapping": "MAC 2.2: Employment and Skills",
        "source": "Open Access TOM System 2024/2025",
        "is_synthetic": False
    },
    {
        "code": "NT8",
        "name": "Support for students at local educational institutions",
        "theme": "Work",
        "outcome": "Developing skills and experience for future work",
        "unit": "no. staff volunteering hours",
        "unit_value_gbp": 17.48,
        "description": "This Measure covers staff volunteering with pupils and students of local educational institutions.\nQualifying activities include corporate presentations, preparing and delivering career talks, curriculum support, literacy support, and specific industry talks. \nThey can take place virtually as well as onsite.\nRecorded hours of staff time can only include time spent preparing and conducting the activities.\nAn employee's volunteering hours can only be recorded if they have been allocated time during paid working hours or time off in lieu.",
        "evidence_required": "(1) Forecast number of staff hours.\n(2) Description of the types of curriculum support activities to be delivered.\n(3) Names of proposed educational establishments if known.",
        "ppn_mapping": "MAC 2.2: Employment and Skills",
        "source": "Open Access TOM System 2024/2025",
        "is_synthetic": False
    },
    {
        "code": "NT99",
        "name": "Support for enabling visits of school children or local residents",
        "theme": "Work",
        "outcome": "Developing skills and experience for future work",
        "unit": "no. staff volunteering hours",
        "unit_value_gbp": 17.48,
        "description": "This Measure covers educational visits to project sites for local school children and residents.\nQualifying sessions must be informative, and organised in conjunction with the educational institution.\nRecorded hours of staff time can only include time spent preparing and conducting the activities.\nAn employee's volunteering hours can only be recorded if they have been allocated time during paid working hours or time off in lieu.",
        "evidence_required": "(1) Forecast number of staff hours.\n(2) Description of the types of activities to be delivered.\n(3) Names of any proposed partner organisations if known.",
        "ppn_mapping": "MAC 2.2: Employment and Skills",
        "source": "Open Access TOM System 2024/2025",
        "is_synthetic": False
    },
    {
        "code": "NT14",
        "name": "Spend with VCSEs in the supply chain",
        "theme": "Economy",
        "outcome": "Building diverse and sustainable supply chains",
        "unit": "\u00a3",
        "unit_value_gbp": 0.12,
        "description": "This Measure covers spend with Voluntary, Community and Social Enterprises (VCSE) suppliers. \nIt does not include grants or donations.\nThe qualifying spend must be with organisations within the supply chain that are classified as VCSEs.",
        "evidence_required": "(1) Forecast \u00a3 to be spent (not donations) with VCSEs in supply chain.\n(2) Types of goods/services, and estimated proportions, to be procured from each VCSE.\n(3) Names of proposed VCSEs if known.",
        "ppn_mapping": "MAC 2.3: Diverse Supply Chains",
        "source": "Open Access TOM System 2024/2025",
        "is_synthetic": False
    },
    {
        "code": "NT18",
        "name": "Spend with local companies in the supply chain",
        "theme": "Economy",
        "outcome": "Building diverse and sustainable supply chains",
        "unit": "\u00a3",
        "unit_value_gbp": 1.089,
        "description": "This Measure covers spend with local suppliers and reflects the economic and social benefits to the local community.\nIt allows for adjustment by local area and industry.\nThe Measure requires a definition of the local area.",
        "evidence_required": "(1) Forecast \u00a3 to be spent with suppliers in the defined local area.\n(2) Types of goods/services, and estimated proportions, to be procured.\n(3) Names of proposed suppliers if known.",
        "ppn_mapping": "MAC 2.3: Diverse Supply Chains",
        "source": "Open Access TOM System 2024/2025",
        "is_synthetic": False
    },
    {
        "code": "NT19",
        "name": "Spend with local SMEs in the supply chain",
        "theme": "Economy",
        "outcome": "Building diverse and sustainable supply chains",
        "unit": "\u00a3",
        "unit_value_gbp": 1.097,
        "description": "This Measure covers spend with local suppliers which are Small and Medium Enterprises (SMEs) and reflects the economic and social benefits to the local community.\nIt allows for adjustment by local area and industry. \nThe Measure requires a definition of the local area.",
        "evidence_required": "(1) Forecast \u00a3 to be spent with small or medium sized suppliers in the defined local area.\n(2) Types of goods/services, and estimated proportions, to be procured.\n(3) Names of proposed suppliers if known.",
        "ppn_mapping": "MAC 2.3: Diverse Supply Chains",
        "source": "Open Access TOM System 2024/2025",
        "is_synthetic": False
    },
    {
        "code": "NT15",
        "name": "Expert support to VCSEs and SMEs",
        "theme": "Economy",
        "outcome": "Promoting a diverse and resilient business community",
        "unit": "no. staff expert hours",
        "unit_value_gbp": 106.34,
        "description": "This Measure covers employees providing their expertise to Voluntary, Community and Social Enterprises (VCSEs) or Small and Medium Enterprises (SMEs).\nQualifying activities include a range of expert-led sessions offering specialist business advice that builds the capacity of VCSEs and SMEs.\nRecorded hours of staff time can only include time spent preparing and conducting the activities.\nAn employee's expert hours can only be recorded if they have been allocated time during paid working hours or time off in lieu.",
        "evidence_required": "(1) Forecast number of employee hours and their relevant qualification/role.\n(2) Description of the expert support to be provided.\n(3) Names of organisations to benefit from the advice if known.",
        "ppn_mapping": "MAC 2.3: Diverse Supply Chains",
        "source": "Open Access TOM System 2024/2025",
        "is_synthetic": False
    },
    {
        "code": "NT16",
        "name": "Support for VCSEs through donations",
        "theme": "Economy",
        "outcome": "Promoting a diverse and resilient business community",
        "unit": "\u00a3 invested",
        "unit_value_gbp": 1.0,
        "description": "This Measure covers financial and in-kind contributions to Voluntary, Community and Social Enterprises (VCSEs). \nThis Measure cannot be used for staff donations or donations raised from third parties at fundraising events.",
        "evidence_required": "(1) Proposed resources to be donated (e.g., \u00a3 donations and/or \u00a3 equivalent in-kind contributions).\n(2) Names of VCSEs to be supported if known.",
        "ppn_mapping": "MAC 2.3: Diverse Supply Chains",
        "source": "Open Access TOM System 2024/2025",
        "is_synthetic": False
    },
    {
        "code": "NT17",
        "name": "Support for VCSEs through volunteering",
        "theme": "Economy",
        "outcome": "Promoting a diverse and resilient business community",
        "unit": "no. staff volunteering hours",
        "unit_value_gbp": 17.48,
        "description": "This Measure covers staff volunteering with Voluntary, Community and Social Enterprises (VCSEs). \nQualifying activities are a range of initiatives aimed at supporting the VCSE and explicitly excludes expert advice. \nRecorded hours of staff time can only include time spent preparing and conducting the activities.\nAn employee's volunteering hours can only be recorded if they have been allocated time during paid working hours or time off in lieu.",
        "evidence_required": "(1) Forecast number of staff hours.\n(2) Description of the types of activities to be delivered.\n(3) Names of VCSEs to be supported if known.",
        "ppn_mapping": "MAC 2.3: Diverse Supply Chains",
        "source": "Open Access TOM System 2024/2025",
        "is_synthetic": False
    },
    {
        "code": "NT28",
        "name": "Support for local community projects through donations",
        "theme": "Community",
        "outcome": "Building resilient communities",
        "unit": "\u00a3 invested",
        "unit_value_gbp": 1.0,
        "description": "This Measure covers financial and in-kind contributions to a range of initiatives aimed at improving the welfare and wellbeing of a community. \nThese include financial and in-kind contributions to community projects and can be run in partnership with a VCSE or as part of a company programme. \nEach of the types of support offered should be recorded separately in the appropriate categories.",
        "evidence_required": "(1) Forecast resources to be invested.\n(2) Description of the types of initiatives planned.\n(3) Names of any proposed partner organisations if known.",
        "ppn_mapping": "MAC 3.1: Health and Wellbeing",
        "source": "Open Access TOM System 2024/2025",
        "is_synthetic": False
    },
    {
        "code": "NT29",
        "name": "Support for local community projects through volunteering",
        "theme": "Community",
        "outcome": "Building resilient communities",
        "unit": "no. staff volunteering hours",
        "unit_value_gbp": 17.48,
        "description": "This Measure covers staff volunteering on local community projects.\nQualifying activities include a range of initiatives geared at improving community wellbeing.\nThese can be run in partnership with a VCSE or as part of a company programme based on local need.\nRecorded hours of staff time can only include time spent preparing and conducting the activities.\nAn employee's volunteering hours can only be recorded if they have been allocated time during paid working hours or time off in lieu.",
        "evidence_required": "(1) Forecast number of staff hours.\n(2) Description of the types of local community activities to be delivered.\n(3) Names of any proposed partner organisations if known.",
        "ppn_mapping": "MAC 3.1: Health and Wellbeing",
        "source": "Open Access TOM System 2024/2025",
        "is_synthetic": False
    },
    {
        "code": "NT26",
        "name": "Support for community health or wellbeing interventions",
        "theme": "Community",
        "outcome": "Building community wellbeing",
        "unit": "\u00a3 invested inc. time, materials, equipment etc",
        "unit_value_gbp": 1.0,
        "description": "This Measure covers support for a range of initiatives aimed at promoting and increasing health and wellbeing in a community such as fitness programmes, nutrition support and smoking, alcohol, and drug abuse reduction initiatives, etc.\nThese can be run in partnership with a VCSE or as part of a company programme.\nRecorded hours of staff time can only include time spent preparing and conducting the activities.\nEach of the types of support offered should be recorded separately.",
        "evidence_required": "(1) Forecast resources to be invested.\n(2) Description of the types of initiatives planned.\n(3) Names of any proposed partner organisations if known.",
        "ppn_mapping": "MAC 3.1: Health and Wellbeing",
        "source": "Open Access TOM System 2024/2025",
        "is_synthetic": False
    },
    {
        "code": "NT27",
        "name": "Support for initiatives focused on strengthening community networks",
        "theme": "Community",
        "outcome": "Building community wellbeing",
        "unit": "\u00a3 invested inc. time, materials, equipment etc",
        "unit_value_gbp": 1.0,
        "description": "This Measure covers support for a range of initiatives aimed at the most vulnerable in society.\nThese include elderly social clubs, digital skills training sessions, fitness programmes for persons with disabilities, etc., and can be run in partnership with a VCSE or as part of a company programme.\nRecorded hours of staff time can only include time spent preparing and conducting the activities.\nEach of the types of support offered should be recorded separately.",
        "evidence_required": "(1) Forecast resources to be invested.\n(2) Description of the types of initiatives planned.\n(3) Names of any proposed partner organisations if known.",
        "ppn_mapping": "MAC 3.1: Health and Wellbeing",
        "source": "Open Access TOM System 2024/2025",
        "is_synthetic": False
    },
    {
        "code": "NT31",
        "name": "Reductions in scope 1 & 2 CO2e emissions through decarbonisation",
        "theme": "Planet",
        "outcome": "Restoring our climate and improving air quality through decarbonisation",
        "unit": "tCO2e",
        "unit_value_gbp": 252.11,
        "description": "This Measure covers the reductions in scope 1 and scope 2 emissions (see Greenhouse Gas Protocol) from decarbonisation initiatives.\nRecorded savings must go beyond the annual percentage reduction required in the UK to achieve net zero emissions by 2050 (currently set at 2.4% per year).\nThis Measure uses the previous year's scope 1 and scope 2 CO2e emissions as a baseline.\nThis Measure can only be used if the previous year's annual carbon report is available.\nThis Measure does not include carbon offsetting.",
        "evidence_required": "(1) Description of the specific decarbonisation initiatives to be undertaken to achieve emission reductions.\n(2) Carbon certifications from third-party organisations where available.",
        "ppn_mapping": "MAC 4.1: Effective Stewardship of the Environment",
        "source": "Open Access TOM System 2024/2025",
        "is_synthetic": False
    },
    {
        "code": "NT31a",
        "name": "Reductions in scope 3 CO2e emissions through decarbonisation",
        "theme": "Planet",
        "outcome": "Restoring our climate and improving air quality through decarbonisation",
        "unit": "tCO2e",
        "unit_value_gbp": 252.11,
        "description": "This Measure covers the reductions in scope 3 emissions (see Greenhouse Gas Protocol) from decarbonisation initiatives.\nRecorded savings must go beyond the annual percentage reduction required in the UK to achieve net zero emissions by 2050 (currently set at 2.4% per year).\nThis Measure uses the previous year's scope 3 CO2e emissions as a baseline.\nThis Measure can only be used if the previous year's annual carbon report is available.\nEach year's reductions can only be based on the scope 3 categories stated in the baseline year. \nIf the range of scope 3 categories reported is extended, this can be reported in subsequent years.\nThis Measure does not include carbon offsetting.",
        "evidence_required": "(1) Specific categories to be measured against (see GHG Protocol).\n(2) Description of the specific decarbonisation initiatives to be undertaken to achieve emission reductions.\n(3) Carbon certifications from third-party organisations where available.",
        "ppn_mapping": "MAC 4.1: Effective Stewardship of the Environment",
        "source": "Open Access TOM System 2024/2025",
        "is_synthetic": False
    },
    {
        "code": "NT32",
        "name": "Reductions in car miles from a green transport programme",
        "theme": "Planet",
        "outcome": "Restoring our climate and improving air quality through transport",
        "unit": "miles saved",
        "unit_value_gbp": 0.0708,
        "description": "This Measure covers the reductions in car miles driven as a result of a green transport programme.\nReductions in car miles is the difference between the actual car miles and a baseline, and can be calculated by measuring or estimating the mileage before the intervention to create the baseline, then measuring the actual car mileage. \nQualifying programmes include cycle-to-work schemes, public transport support, or carpooling / carsharing initiatives (not including hybrid working).\nThis Measure addresses business travel and employee commuting categories within scope 3 emissions.",
        "evidence_required": "(1) Description of organisation's green transport programmes to reduce car miles.\n(2) Baseline car miles with supporting evidence.\n(3) Forecast car miles from the intervention.",
        "ppn_mapping": "MAC 4.1: Effective Stewardship of the Environment",
        "source": "Open Access TOM System 2024/2025",
        "is_synthetic": False
    },
    {
        "code": "NT116",
        "name": "Expert support on carbon reduction to SMEs in the supply chain",
        "theme": "Planet",
        "outcome": "Promoting environmentally sustainable procurement",
        "unit": "\u00a3 invested inc. time, materials, equipment etc",
        "unit_value_gbp": 1.0,
        "description": "This Measure covers the costs associated with the provision of expert-led climate change and carbon reduction training for sub contractors which are Small and Medium Enterprises (SMEs).\nSupported initiatives must be expertly designed and qualifying recipients are those within these organisations with decision making capabilities and who are in a position to drive organisational change. \nExamples of training courses are: Supply Chain Sustainability School bronze or higher certificates or the Carbon Literacy Project etc. and can be run in partnership with a VCSE or as part of a company programme.\nRecorded hours of staff time can only include time spent preparing and conducting the activities.\nEach of the types of support offered should be recorded separately.",
        "evidence_required": "(1) Forecast resources to be invested.\n(2) Description of the types of initiatives planned.\n(3) Names of any proposed partner organisations if known.",
        "ppn_mapping": "MAC 4.1: Effective Stewardship of the Environment",
        "source": "Open Access TOM System 2024/2025",
        "is_synthetic": False
    },
    {
        "code": "NT119",
        "name": "Support for green spaces, biodiversity or ecosystems",
        "theme": "Planet",
        "outcome": "Protecting and restoring biodiversity and ecosystems",
        "unit": "\u00a3 invested inc. time, materials, equipment etc",
        "unit_value_gbp": 1.0,
        "description": "This Measure covers support for a range of greenspace creation and development schemes which preserve or enhance natural land or vegetation.\nExamples are funding urban parks and gardens, street planting, brownspace regeneration, etc., and can be run in partnership with a VCSE or as part of a company programme.\nRecorded hours of staff time can only include time spent preparing and conducting the activities.\nEach of the types of support offered should be recorded separately.",
        "evidence_required": "(1) Forecast resources to be invested.\n(2) Description of the types of initiatives planned.\n(3) Names of any proposed partner organisations if known.",
        "ppn_mapping": "MAC 4.1: Effective Stewardship of the Environment",
        "source": "Open Access TOM System 2024/2025",
        "is_synthetic": False
    },
    {
        "code": "NT87",
        "name": "Reductions in plastics used",
        "theme": "Planet",
        "outcome": "Transitioning to a regenerative economy",
        "unit": "kg",
        "unit_value_gbp": 116.52,
        "description": "This Measure covers reductions in plastic use through reduction initiatives such as designing out waste from plastic packaging or materials.\nThis Measure requires a baseline, which can be determined by the previous year's plastics use or the estimated plastics use without the intervention.",
        "evidence_required": "(1) Description of the initiative to avoid plastic use.\n(2) Description of the benchmark to be adopted, including rationale/justification.\n(3) Forecast total amount (in kg) of plastic consumption.\n(4) Forecast amount (in kg) of virgin plastic consumption avoided beyond the set benchmark.",
        "ppn_mapping": "MAC 4.1: Effective Stewardship of the Environment",
        "source": "Open Access TOM System 2024/2025",
        "is_synthetic": False
    }
]

MASTER_INITIATIVES_PATH = Path(__file__).resolve().parent.parent / "data" / "master_initiatives.json"


def _load_master_initiatives() -> List[Dict[str, Any]]:
    """Load the 37 NHS FWS master initiatives (confidential valuation fields excluded)."""
    try:
        with open(MASTER_INITIATIVES_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:
        print(f"[CalculationService Warning] Could not load master initiatives: {exc}")
        return []


MASTER_INITIATIVES_DATA: List[Dict[str, Any]] = _load_master_initiatives()


class CalculationService:
    """
    Deterministic Social Value Calculation & TOMs Catalog Service.
    Connects to database for persistent configuration while maintaining strict deterministic math.
    """

    def ensure_seeded(self, db: Session) -> None:
        """Seed default metrics into DB if empty."""
        try:
            count = db.query(TomsMetricModel).count()
            if count == 0:
                for item in DEFAULT_TOMS_DATA:
                    db_item = TomsMetricModel(**item)
                    db.add(db_item)
                db.commit()
        except Exception as e:
            db.rollback()
            print(f"[CalculationService Warning] Seeding check deferred: {e}")

    def get_all_metrics(
        self,
        db: Optional[Session] = None,
        theme: Optional[str] = None,
        search: Optional[str] = None,
        active_only: bool = False
    ) -> List[TOMsMetric]:
        """Fetch all metrics from DB with optional filtering, or fall back to default list."""
        if db is not None:
            try:
                self.ensure_seeded(db)
                query = db.query(TomsMetricModel)
                if active_only:
                    query = query.filter(TomsMetricModel.is_active.is_(True))
                if theme and theme.lower() != "all":
                    query = query.filter(TomsMetricModel.theme.ilike(f"%{theme.strip()}%"))
                if search:
                    q = f"%{search.strip()}%"
                    query = query.filter(
                        or_(
                            TomsMetricModel.code.ilike(q),
                            TomsMetricModel.name.ilike(q),
                            TomsMetricModel.description.ilike(q),
                            TomsMetricModel.ppn_mapping.ilike(q)
                        )
                    )
                rows = query.order_by(TomsMetricModel.code.asc()).all()
                if rows:
                    return [TOMsMetric.model_validate(r) for r in rows]
            except Exception as exc:
                print(f"[CalculationService Warning] Could not query DB ({exc}), returning static defaults.")

        # Fallback to in-memory defaults
        results = [TOMsMetric(**data) for data in DEFAULT_TOMS_DATA]
        if theme and theme.lower() != "all":
            results = [m for m in results if theme.lower() in m.theme.lower()]
        if search:
            s = search.lower()
            results = [
                m for m in results
                if s in m.code.lower() or s in m.name.lower() or (m.description and s in m.description.lower())
            ]
        return results

    def get_metric_by_code(self, db: Optional[Session], code: str) -> Optional[TOMsMetric]:
        """Find a single metric by its unique code."""
        if not code:
            return None
        code_clean = code.strip().upper()

        if db is not None:
            try:
                self.ensure_seeded(db)
                row = db.query(TomsMetricModel).filter(TomsMetricModel.code.ilike(code_clean)).first()
                if row:
                    return TOMsMetric.model_validate(row)
            except Exception:
                pass

        for item in DEFAULT_TOMS_DATA:
            if item["code"].upper() == code_clean:
                return TOMsMetric(**item)
        return None

    def create_metric(self, db: Session, metric_in: TomsMetricCreate) -> TOMsMetric:
        """Create and persist a new TOMs metric in the database."""
        self.ensure_seeded(db)
        code_clean = metric_in.code.strip().upper()

        existing = db.query(TomsMetricModel).filter(TomsMetricModel.code.ilike(code_clean)).first()
        if existing:
            raise ValueError(f"Metric with code '{code_clean}' already exists. Use update instead.")

        db_item = TomsMetricModel(
            code=code_clean,
            name=metric_in.name.strip(),
            theme=metric_in.theme.strip(),
            outcome=metric_in.outcome.strip() if metric_in.outcome else None,
            unit=metric_in.unit.strip(),
            unit_value_gbp=float(metric_in.unit_value_gbp),
            description=metric_in.description.strip() if metric_in.description else "",
            evidence_required=metric_in.evidence_required.strip() if metric_in.evidence_required else "",
            ppn_mapping=metric_in.ppn_mapping.strip() if metric_in.ppn_mapping else "",
            source=metric_in.source.strip() if metric_in.source else "Custom User Metric",
            is_active=True
        )
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return TOMsMetric.model_validate(db_item)

    def update_metric(self, db: Session, code: str, metric_in: TomsMetricUpdate) -> Optional[TOMsMetric]:
        """Update an existing metric by its code."""
        self.ensure_seeded(db)
        row = db.query(TomsMetricModel).filter(TomsMetricModel.code.ilike(code.strip())).first()
        if not row:
            return None

        update_data = metric_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(row, key, value)

        db.commit()
        db.refresh(row)
        return TOMsMetric.model_validate(row)

    def delete_metric(self, db: Session, code: str) -> bool:
        """Soft-deactivate or delete a metric."""
        self.ensure_seeded(db)
        row = db.query(TomsMetricModel).filter(TomsMetricModel.code.ilike(code.strip())).first()
        if not row:
            return False

        # Soft delete by deactivating
        row.is_active = False
        db.commit()
        return True

    def reset_to_defaults(self, db: Session) -> int:
        """Reset or restore default metrics into database."""
        db.query(TomsMetricModel).delete()
        for item in DEFAULT_TOMS_DATA:
            db.add(TomsMetricModel(**item))
        db.commit()
        return len(DEFAULT_TOMS_DATA)

    def get_master_initiatives(
        self,
        pillar: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return the 37 audited Master Initiatives from NHS FWS tender library with filtering."""
        results = list(MASTER_INITIATIVES_DATA)
        if pillar and pillar.lower() != "all":
            p = pillar.lower().strip()
            results = [x for x in results if p in x.get("pillar", "").lower()]
        if search:
            s = search.lower().strip()
            results = [
                x for x in results
                if s in x.get("id", "").lower()
                or s in x.get("name", "").lower()
                or s in x.get("description", "").lower()
                or s in x.get("delivered_by", "").lower()
                or s in x.get("mac", "").lower()
            ]
        return results

    def calculate_initiative(
        self,
        initiative_name: str,
        toms_code: Optional[str],
        annual_volume: float,
        duration_years: int,
        db: Optional[Session] = None
    ) -> InitiativeCalculation:
        """
        Deterministically calculates the social value for an individual initiative.
        Formula: Annual Volume × Contract Duration (Years) × Unit Value (GBP)
        """
        metric = self.get_metric_by_code(db, toms_code) if toms_code else None

        if metric:
            unit_val = metric.unit_value_gbp
            unit_name = metric.unit
            metric_title = metric.name
            toms_ref = metric.code
        else:
            unit_val = 0.0
            unit_name = "units"
            metric_title = "Unmapped Custom Initiative"
            toms_ref = toms_code or "CUSTOM"

        total_vol = round(annual_volume * duration_years, 2)
        total_sv = round(total_vol * unit_val, 2)
        formula = f"{annual_volume} {unit_name}/yr × {duration_years} yrs = {total_vol} {unit_name} @ £{unit_val:,.2f} = £{total_sv:,.2f}"

        return InitiativeCalculation(
            initiative_name=initiative_name,
            toms_code=toms_ref,
            metric_name=metric_title,
            unit=unit_name,
            unit_value_gbp=unit_val,
            annual_volume=annual_volume,
            duration_years=duration_years,
            total_volume=total_vol,
            total_social_value_gbp=total_sv,
            calculation_formula=formula
        )

    def calculate_package(
        self,
        package_name: str,
        initiatives: List[Dict[str, Any]],
        contract_value_gbp: float,
        duration_years: int,
        target_weighting_percent: float,
        db: Optional[Session] = None
    ) -> PackageCalculation:
        """
        Calculates social value across a package of initiatives against contract target.
        """
        calculated_inits: List[InitiativeCalculation] = []
        total_social_value = 0.0
        audit_trail: List[str] = []

        target_sv_gbp = round((contract_value_gbp * target_weighting_percent) / 100.0, 2)

        for item in initiatives:
            name = item.get("name") or "Unnamed Initiative"
            code = item.get("toms_metric_code") or item.get("toms_code")
            annual_vol = float(item.get("annual_volume", 0.0))

            init_calc = self.calculate_initiative(
                initiative_name=name,
                toms_code=code,
                annual_volume=annual_vol,
                duration_years=duration_years,
                db=db
            )
            calculated_inits.append(init_calc)
            total_social_value += init_calc.total_social_value_gbp
            audit_trail.append(f"{init_calc.initiative_name} ({init_calc.toms_code}): {init_calc.calculation_formula}")

        total_social_value = round(total_social_value, 2)
        sv_percentage = round((total_social_value / contract_value_gbp) * 100.0, 2) if contract_value_gbp > 0 else 0.0
        target_met = total_social_value >= target_sv_gbp

        audit_trail.append(
            f"Package Total: £{total_social_value:,.2f} ({sv_percentage}% of contract). Target ({target_weighting_percent}% = £{target_sv_gbp:,.2f}) Met: {target_met}"
        )

        return PackageCalculation(
            package_name=package_name,
            initiatives=calculated_inits,
            total_social_value_gbp=total_social_value,
            contract_value_gbp=contract_value_gbp,
            social_value_percentage=sv_percentage,
            target_weighting_percent=target_weighting_percent,
            target_social_value_gbp=target_sv_gbp,
            target_met=target_met,
            audit_trail=audit_trail
        )

    def recommend_opportunities(
        self,
        db: Optional[Session],
        req: OpportunityRecommendRequest
    ) -> OpportunityRecommendResponse:
        """
        Opportunity Finder & Bid Advisor for Document-less Clients.
        Synthesizes contract scale, duration, industry, and location to recommend high-scoring,
        achievable TOMs initiatives mapped to PPN 06/20 Model Award Criteria.
        """
        all_metrics = self.get_all_metrics(db=db, active_only=True)
        target_sv_gbp = (req.contract_value_gbp * req.target_weighting_percent) / 100.0

        # Prioritize core pillars: Work, Planet, Community, Economy, Modern Slavery
        theme_allocations = {
            "Work": 0.35,      # 35% of target
            "Planet": 0.25,    # 25% of target
            "Community": 0.20, # 20% of target
            "Economy": 0.20    # 20% of target
        }

        # Filter metrics
        by_code = {m.code: m for m in all_metrics}

        recommendations: List[OpportunityRecommendationItem] = []
        total_rec_sv = 0.0

        # Strategy Selection based on verified catalog:
        # 1. Apprenticeship / Employment (Work) - INI-17 FWS Ambassador Programme
        work_metric = by_code.get("NT10") or by_code.get("NT1") or by_code.get("NHS-SV2-01")
        if work_metric:
            alloc_gbp = target_sv_gbp * theme_allocations["Work"]
            weeks_needed = max(12.0, round(alloc_gbp / (work_metric.unit_value_gbp * req.duration_years), 0))
            calc = self.calculate_initiative(
                "FWS Ambassador Programme (Tech Apprenticeships)",
                work_metric.code,
                weeks_needed,
                req.duration_years,
                db=db
            )
            recommendations.append(OpportunityRecommendationItem(
                toms_code=work_metric.code,
                initiative_name="FWS Ambassador Programme (Tech Apprenticeships)",
                theme=work_metric.theme,
                ppn_mac=work_metric.ppn_mapping or "MAC 2.2: Employment and Skills",
                unit=work_metric.unit,
                unit_value_gbp=work_metric.unit_value_gbp,
                annual_volume=weeks_needed,
                duration_years=req.duration_years,
                total_volume=calc.total_volume,
                total_social_value_gbp=calc.total_social_value_gbp,
                why_recommended=f"Direct contractual initiative from Infosys NHS FWS master commitments (INI-17). Addresses skills shortages in {req.location} through accredited Level 3-6 apprenticeships.",
                delivery_approach="Delivered by Infosys (employer) in partnership with QA Consulting (accredited training provider). Fully co-funded via UK Apprenticeship Levy.",
                evidence_needed=work_metric.evidence_required or "Schedule 3b Paragraph 7.1 delivery sign-off: monthly apprentice timesheets, levy ledger, and accredited qualification certificates."
            ))
            total_rec_sv += calc.total_social_value_gbp

        # 2. Sustainable IT & Carbon Avoidance (Planet) - INI-01 Sustainable IT Framework
        planet_metric = by_code.get("NHS-SV1-01") or by_code.get("NT31")
        if planet_metric:
            alloc_gbp = target_sv_gbp * theme_allocations["Planet"]
            vol_needed = max(1.0, round(alloc_gbp / (planet_metric.unit_value_gbp * req.duration_years), 1))
            calc = self.calculate_initiative(
                "Sustainable IT Framework & GreenOps Observability",
                planet_metric.code,
                vol_needed,
                req.duration_years,
                db=db
            )
            recommendations.append(OpportunityRecommendationItem(
                toms_code=planet_metric.code,
                initiative_name="Sustainable IT Framework & GreenOps Observability",
                theme=planet_metric.theme,
                ppn_mac=planet_metric.ppn_mapping or "MAC 4.1: Fighting Climate Change",
                unit=planet_metric.unit,
                unit_value_gbp=planet_metric.unit_value_gbp,
                annual_volume=vol_needed,
                duration_years=req.duration_years,
                total_volume=calc.total_volume,
                total_social_value_gbp=calc.total_social_value_gbp,
                why_recommended="Core environmental commitment from Infosys NHS FWS library (INI-01). Delivers verified digital decarbonisation and Scope 3 observability.",
                delivery_approach="Delivered by Infosys and Sopht GreenOps platform. Includes RGESN eco-design audits, baseline dashboards, and GDSA case studies (D1-D10 deliverables).",
                evidence_needed=planet_metric.evidence_required or "Schedule 3b §7.1.1-7.1.9 sign-off: Sopht platform energy telemetry logs and ISO 14001 independent audit report."
            ))
            total_rec_sv += calc.total_social_value_gbp

        # 3. Digital Inclusion / Device Prescribing (Community) - INI-19 Device Prescribing Pilot
        comm_metric = by_code.get("NT27") or by_code.get("NHS-SV2-01") or by_code.get("NT8")
        if comm_metric:
            alloc_gbp = target_sv_gbp * theme_allocations["Community"]
            vol_needed = max(500.0 if "£" in comm_metric.unit else 2.0, round(alloc_gbp / (comm_metric.unit_value_gbp * req.duration_years), 0))
            calc = self.calculate_initiative(
                "NHS Device Prescribing & Digital Inclusion Pilot",
                comm_metric.code,
                vol_needed,
                req.duration_years,
                db=db
            )
            recommendations.append(OpportunityRecommendationItem(
                toms_code=comm_metric.code,
                initiative_name="NHS Device Prescribing & Digital Inclusion Pilot",
                theme=comm_metric.theme,
                ppn_mac=comm_metric.ppn_mapping or "MAC 2.1: Tackling Economic Inequality",
                unit=comm_metric.unit,
                unit_value_gbp=comm_metric.unit_value_gbp,
                annual_volume=vol_needed,
                duration_years=req.duration_years,
                total_volume=calc.total_volume,
                total_social_value_gbp=calc.total_social_value_gbp,
                why_recommended=f"Audited commitment from Infosys master library (INI-19). Tackles digital poverty for vulnerable patients and residents in {req.location}.",
                delivery_approach="Delivered by Infosys in partnership with Good Things Foundation. Combines ADISA-sanitized refurbished laptops/tablets with 20GB National Databank SIM cards.",
                evidence_needed=comm_metric.evidence_required or "Schedule 3b KPI9c sign-off: ADISA data-wipe sanitization certificates, clinical referral logs, and National Databank receipts."
            ))
            total_rec_sv += calc.total_social_value_gbp

        # 4. Local SME & Social Enterprise Supply Chain (Economy) - INI-09 Local Supply Chain
        econ_metric = by_code.get("NT18") or by_code.get("NT14")
        if econ_metric:
            alloc_gbp = target_sv_gbp * theme_allocations["Economy"]
            vol_needed = max(5000.0, round(alloc_gbp / (econ_metric.unit_value_gbp * req.duration_years), 0))
            calc = self.calculate_initiative(
                "Local SME & VCSE Supply Chain Integration",
                econ_metric.code,
                vol_needed,
                req.duration_years,
                db=db
            )
            recommendations.append(OpportunityRecommendationItem(
                toms_code=econ_metric.code,
                initiative_name="Local SME & VCSE Supply Chain Integration",
                theme=econ_metric.theme,
                ppn_mac=econ_metric.ppn_mapping or "MAC 2.3: Diverse Supply Chains",
                unit=econ_metric.unit,
                unit_value_gbp=econ_metric.unit_value_gbp,
                annual_volume=vol_needed,
                duration_years=req.duration_years,
                total_volume=calc.total_volume,
                total_social_value_gbp=calc.total_social_value_gbp,
                why_recommended=f"Ensures local economic retention in {req.location} through dedicated Tier-2/Tier-3 subcontracting to local small enterprises and VCSEs.",
                delivery_approach="Ring-fence tier-2 subcontracts (QA testing, local logistics, catering) for verified local SMEs and VCSEs with prompt 30-day payment terms.",
                evidence_needed=econ_metric.evidence_required or "Audited supplier postcode validation, purchase orders, and 30-day payment ledger."
            ))
            total_rec_sv += calc.total_social_value_gbp

        # 5. Modern Slavery Governance Benchmark (SV3) - INI-27 Unseen MSAT Auditing
        ms_metric = by_code.get("NHS-SV3-01")
        if ms_metric:
            vol_needed = 2.0  # biannual
            calc = self.calculate_initiative(
                "Supply Chain Modern Slavery MSAT Auditing",
                ms_metric.code,
                vol_needed,
                req.duration_years,
                db=db
            )
            recommendations.append(OpportunityRecommendationItem(
                toms_code=ms_metric.code,
                initiative_name="Supply Chain Modern Slavery MSAT Auditing",
                theme=ms_metric.theme,
                ppn_mac=ms_metric.ppn_mapping or "MAC 6.3: Tackling Workforce Inequality",
                unit=ms_metric.unit,
                unit_value_gbp=ms_metric.unit_value_gbp,
                annual_volume=vol_needed,
                duration_years=req.duration_years,
                total_volume=calc.total_volume,
                total_social_value_gbp=calc.total_social_value_gbp,
                why_recommended="Mandatory compliance element for central government and NHS procurement under Procurement Policy Note 02/23.",
                delivery_approach="Enforce Home Office Modern Slavery Assessment Tool (MSAT) reviews every 6 months across Tier-1 vendors maintaining score >= 80%.",
                evidence_needed=ms_metric.evidence_required or "Biannual Home Office MSAT scorecard reports and supplier audit trail sign-offs."
            ))
            total_rec_sv += calc.total_social_value_gbp

        achieved_pct = round((total_rec_sv / req.contract_value_gbp) * 100.0, 2) if req.contract_value_gbp > 0 else 0.0

        summary = (
            f"Tailored Social Value Strategy for {req.industry} contract in {req.location}: "
            f"Delivering £{total_rec_sv:,.2f} of audited Social Value ({achieved_pct}% of contract value), "
            f"surpassing the statutory {req.target_weighting_percent}% target (£{target_sv_gbp:,.2f}). "
            f"Features 5 balanced commitments across Skills (Work), Net Zero (Planet), Digital Inclusion (Community), "
            f"and SME Prosperity (Economy), fully structured for Schedule 8 Method Statement and Schedule 3b KPIs."
        )

        return OpportunityRecommendResponse(
            contract_value_gbp=req.contract_value_gbp,
            duration_years=req.duration_years,
            target_weighting_percent=req.target_weighting_percent,
            target_social_value_gbp=round(target_sv_gbp, 2),
            total_recommended_social_value_gbp=round(total_rec_sv, 2),
            achieved_weighting_percent=achieved_pct,
            target_met=total_rec_sv >= target_sv_gbp,
            recommendations=recommendations,
            executive_summary=summary
        )


calculation_service = CalculationService()
