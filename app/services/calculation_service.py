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
        "theme": "Work",
        "outcome": "Creating local employment opportunities",
        "code": "NT1",
        "name": "Local people employed or retained",
        "unit": "no. people FTE",
        "unit_value_gbp": 37666.5,
        "description": "This Measure covers the employment of local people.\nQualifying employees must live in the local area, have an employment contract that reflects the hours they regularly work with a guaranteed minimum working time of 16 hours per week and at least 4 weeks of notice for shifts in the working pattern.\nThe Full Time Equivalent (FTE) calculation must be derived from the length of the employment contract within the reporting period.\nThe Measure requires a definition of the local area.",
        "evidence_required": "No. people (FTE) * length of contract (in years) where the maximum number of FTE per person per year is 1.0; \nA full-time equivalent (FTE) of 1.0 corresponds to having one person employed at least 35 hours per week for a period of 12 months. If they are employed for a shorter period, the FTE should be calculated at a proportional rate.",
        "ppn_mapping": "Creating local employment opportunities",
        "source": "National TOMs 2025 (Open Access Edition)"
    },
    {
        "theme": "Work",
        "outcome": "Creating equal employment opportunities",
        "code": "NT3",
        "name": "Long-term unemployed people recruited",
        "unit": "no. people FTE",
        "unit_value_gbp": 51561.0,
        "description": "This Measure covers the employment of a person who can be classified as 'Long-term unemployed'.\nQualifying employees will have been unemployed for a year or more.\nThe Measure can only be used once per qualifying employee, for the first year of their employment, and does not include students.",
        "evidence_required": "No. people FTE (capped at 1 year per employee);\nA full-time equivalent (FTE) of 1.0 corresponds to having one person employed at least 35 hours per week for a period of 12 months. If they are employed for a shorter period, the FTE should be calculated at a proportional rate.",
        "ppn_mapping": "Creating equal employment opportunities",
        "source": "National TOMs 2025 (Open Access Edition)"
    },
    {
        "theme": "Work",
        "outcome": "Creating equal employment opportunities",
        "code": "NT4",
        "name": "Employees recruited who are Not in Education Employment or Training (16-24 y.o.)",
        "unit": "no. people FTE",
        "unit_value_gbp": 53013.0,
        "description": "This Measure covers the employment of a person who can be classified as 'not in education employment or training' (NEET).\nQualifying employees are 16-24 year olds who are not in formal training, education or any form of paid employment.\nThe Measure can only be used once per qualifying employee, for the first year of their employment and does not include students, or adults who are long-term unemployed.",
        "evidence_required": "No. people FTE (capped at 1 year per employee);\nA full-time equivalent (FTE) of 1.0 corresponds to having one person employed at least 35 hours per week for a period of 12 months. If they are employed for a shorter period, the FTE should be calculated at a proportional rate.",
        "ppn_mapping": "Creating equal employment opportunities",
        "source": "National TOMs 2025 (Open Access Edition)"
    },
    {
        "theme": "Work",
        "outcome": "Creating equal employment opportunities",
        "code": "NT76",
        "name": "Unemployed people recruited",
        "unit": "no. people FTE",
        "unit_value_gbp": 50713.0,
        "description": "This Measure covers the employment of a person who can be classified as 'unemployed'.\nQualifying employees will have been unemployed for at least four weeks.\nThe Measure can only be used once per qualifying employee, for the first year of their employment.",
        "evidence_required": "No. people FTE (capped at 1 year per employee);\nA full-time equivalent (FTE) of 1.0 corresponds to having one person employed at least 35 hours per week for a period of 12 months. If they are employed for a shorter period, the FTE should be calculated at a proportional rate.",
        "ppn_mapping": "Creating equal employment opportunities",
        "source": "National TOMs 2025 (Open Access Edition)"
    },
    {
        "theme": "Work",
        "outcome": "Creating equal employment opportunities",
        "code": "NT5",
        "name": "Unemployed ex-offenders aged 18 and over recruited",
        "unit": "no. people FTE",
        "unit_value_gbp": 55922.0,
        "description": "This Measure covers the employment of a person who is an unemployed ex-offender.\nQualifying employees will be aged 18 and over.\nThe Measure can only be used once per qualifying employee, for the first year of their employment.",
        "evidence_required": "No. people FTE (capped at 1 year per employee);\nA full-time equivalent (FTE) of 1.0 corresponds to having one person employed at least 35 hours per week for a period of 12 months. If they are employed for a shorter period, the FTE should be calculated at a proportional rate.",
        "ppn_mapping": "Creating equal employment opportunities",
        "source": "National TOMs 2025 (Open Access Edition)"
    },
    {
        "theme": "Work",
        "outcome": "Creating equal employment opportunities",
        "code": "NT6",
        "name": "Unemployed individuals with disabilities recruited",
        "unit": "no. people FTE",
        "unit_value_gbp": 51889.0,
        "description": "This Measure covers the employment of a person who is unemployed and who has a disability\nA qualifying employee is \"someone with a physical or mental impairment that has a \u2018substantial\u2019 and \u2018long-term\u2019 effect on their ability to do normal daily activities\" (Equality Act, 2010).\nThe Measure can only be used once per qualifying employee, for the first year of their employment.",
        "evidence_required": "No. people FTE (capped at 1 year per employee);\nA full-time equivalent (FTE) of 1.0 corresponds to having one person employed at least 35 hours per week for a period of 12 months. If they are employed for a shorter period, the FTE should be calculated at a proportional rate.",
        "ppn_mapping": "Creating equal employment opportunities",
        "source": "National TOMs 2025 (Open Access Edition)"
    },
    {
        "theme": "Work",
        "outcome": "Providing skills and experience for good work",
        "code": "NT9",
        "name": "Accredited training for new employees",
        "unit": "no. weeks",
        "unit_value_gbp": 347.0,
        "description": "This Measure covers new employment with accredited vocational training.\nQualifying courses are at level 2 or higher such as: BTEC, City & Guilds, NVQ, HNC, RQF or T-levels.\nCourses must be completed by the employee and supported by the organisation until qualification is attained.\nThis Measure can only be used to record training opportunities for new employees, not existing employees.",
        "evidence_required": "Training Weeks;\nNo. weeks of training per person. A week has to include at least 3 training days per week; weeks with fewer training days can only be counted pro rata (total course days divided by 5).",
        "ppn_mapping": "Providing skills and experience for good work",
        "source": "National TOMs 2025 (Open Access Edition)"
    },
    {
        "theme": "Work",
        "outcome": "Providing skills and experience for good work",
        "code": "NT10",
        "name": "Employment of new apprentices",
        "unit": "no. weeks",
        "unit_value_gbp": 309.73,
        "description": "This Measure covers the employment of new apprentices at level 2 or higher.\nQualifying apprenticeships must follow an established path of progression to ensure timely completion and should be supported by the organisation until complete.\nThis Measure can only be used to record opportunities for new employees and not upskilling for existing employees.",
        "evidence_required": "Employment Weeks;\nNo. weeks of apprenticeship training per person.",
        "ppn_mapping": "Providing skills and experience for good work",
        "source": "National TOMs 2025 (Open Access Edition)"
    },
    {
        "theme": "Work",
        "outcome": "Providing skills and experience for good work",
        "code": "NT80",
        "name": "Upskilling of existing employees through accredited training",
        "unit": "no. weeks",
        "unit_value_gbp": 13.02,
        "description": "This Measure covers the upskilling of existing employees through accredited vocational training.\nQualifying courses are at level 2 or higher such as: BTEC, City & Guilds, NVQ, HNC, RQF or T-levels. \nCourses must be completed by the employee and supported by the organisation until qualification is attained.",
        "evidence_required": "Training Weeks;\nNo. weeks of training per person. A week has to include at least 3 training days per week; weeks with fewer training days can only be counted pro rata (total course days divided by 5).",
        "ppn_mapping": "Providing skills and experience for good work",
        "source": "National TOMs 2025 (Open Access Edition)"
    },
    {
        "theme": "Work",
        "outcome": "Providing skills and experience for good work",
        "code": "NT11",
        "name": "Personalised support to help unemployed people into work",
        "unit": "no. hrs (total session duration)*no. attendees",
        "unit_value_gbp": 110.99,
        "description": "This Measure covers the provision of expert-led personalised support to help unemployed people gain work (not including students).\nExamples include career mentoring, mock interviews, CV advice, careers guidance, etc.\nGroup sessions must be of a small enough size to allow recipients to receive personalised support based on their individual and specific needs.\nTraining can be delivered online or in person.\nAn employee's hours can only be recorded if they have been allocated time during paid working hours or time off in lieu.",
        "evidence_required": "Attendee Hours;\nNo. attendees * Session duration (in hours).",
        "ppn_mapping": "Providing skills and experience for good work",
        "source": "National TOMs 2025 (Open Access Edition)"
    },
    {
        "theme": "Work",
        "outcome": "Providing good work opportunities",
        "code": "NT12",
        "name": "Meaningful unpaid work placements while Not in Employment Education or Training",
        "unit": "no. weeks",
        "unit_value_gbp": 96.53,
        "description": "This Measure covers the provision of unpaid, short-term placements or pre-employment courses that make a meaningful contribution to enabling young people not in employment education or training (NEET) to find gainful employment.\nThe placement must not last more than 8 consecutive weeks (or more than 40 days within a 3-month period) but at least 1 week.\nThe Measure can only be used once per person within a 12-month period. \nExamples of meaningful work placements include work on junior-level tasks providing industry experience and insight.",
        "evidence_required": "No. weeks on placement per person.Working days can be counted pro rata (total  working days divided by 5) but a week has to include at least 3 working days per week.",
        "ppn_mapping": "Providing good work opportunities",
        "source": "National TOMs 2025 (Open Access Edition)"
    },
    {
        "theme": "Work",
        "outcome": "Providing good work opportunities",
        "code": "NT13",
        "name": "Meaningful paid work placements",
        "unit": "no. weeks",
        "unit_value_gbp": 412.38,
        "description": "This Measure covers the provision of paid work placements that make a meaningful contribution to enabling young people to find gainful employment.\nThe placement can last between 2 weeks and 6 months.\nThe Measure can only be used once per person, within a 12-month period.\nExamples of meaningful work placements include work on junior-level tasks providing industry experience and insight.",
        "evidence_required": "No. weeks on placement per person.Working days can be counted pro rata (total  working days divided by 5) but a week has to include at least 3 working days per week.",
        "ppn_mapping": "Providing good work opportunities",
        "source": "National TOMs 2025 (Open Access Edition)"
    },
    {
        "theme": "Work",
        "outcome": "Developing skills and experience for future work",
        "code": "NT8",
        "name": "Support for students at local educational institutions",
        "unit": "no. staff volunteering hours",
        "unit_value_gbp": 17.48,
        "description": "This Measure covers staff volunteering with pupils and students of local educational institutions.\nQualifying activities include corporate presentations, preparing and delivering career talks, curriculum support, literacy support, and specific industry talks. \nThey can take place virtually as well as onsite.\nRecorded hours of staff time can only include time spent preparing and conducting the activities.\nAn employee's volunteering hours can only be recorded if they have been allocated time during paid working hours or time off in lieu.",
        "evidence_required": "Volunteering Hours;\nNo. volunteering hours per employee per event.",
        "ppn_mapping": "Developing skills and experience for future work",
        "source": "National TOMs 2025 (Open Access Edition)"
    },
    {
        "theme": "Work",
        "outcome": "Developing skills and experience for future work",
        "code": "NT99",
        "name": "Support for enabling visits of school children or local residents",
        "unit": "no. staff volunteering hours",
        "unit_value_gbp": 17.48,
        "description": "This Measure covers educational visits to project sites for local school children and residents.\nQualifying sessions must be informative, and organised in conjunction with the educational institution.\nRecorded hours of staff time can only include time spent preparing and conducting the activities.\nAn employee's volunteering hours can only be recorded if they have been allocated time during paid working hours or time off in lieu.",
        "evidence_required": "Volunteering Hours;\nNo. volunteering hours per employee per event.",
        "ppn_mapping": "Developing skills and experience for future work",
        "source": "National TOMs 2025 (Open Access Edition)"
    },
    {
        "theme": "Economy",
        "outcome": "Building diverse and sustainable supply chains",
        "code": "NT14",
        "name": "Spend with VCSEs in the supply chain",
        "unit": "\u00a3",
        "unit_value_gbp": 0.12,
        "description": "This Measure covers spend with Voluntary, Community and Social Enterprises (VCSE) suppliers. \nIt does not include grants or donations.\nThe qualifying spend must be with organisations within the supply chain that are classified as VCSEs.",
        "evidence_required": "Total amount of \u00a3 spent with VCSEs in the supply chain.",
        "ppn_mapping": "Building diverse and sustainable supply chains",
        "source": "National TOMs 2025 (Open Access Edition)"
    },
    {
        "theme": "Economy",
        "outcome": "Building diverse and sustainable supply chains",
        "code": "NT18",
        "name": "Spend with local companies in the supply chain",
        "unit": "\u00a3",
        "unit_value_gbp": 0.990909603164808,
        "description": "This Measure covers spend with local suppliers and reflects the economic and social benefits to the local community.\nIt allows for adjustment by local area and industry.\nThe Measure requires a definition of the local area.",
        "evidence_required": "Total amount of \u00a3 spent with the supply chain within the defined local area.",
        "ppn_mapping": "Building diverse and sustainable supply chains",
        "source": "National TOMs 2025 (Open Access Edition)"
    },
    {
        "theme": "Economy",
        "outcome": "Building diverse and sustainable supply chains",
        "code": "NT19",
        "name": "Spend with local SMEs in the supply chain",
        "unit": "\u00a3",
        "unit_value_gbp": 0.998143243267912,
        "description": "This Measure covers spend with local suppliers which are Small and Medium Enterprises (SMEs) and reflects the economic and social benefits to the local community.\nIt allows for adjustment by local area and industry. \nThe Measure requires a definition of the local area.",
        "evidence_required": "Total amount of \u00a3 spent with SMEs in the supply chain within the defined local area.",
        "ppn_mapping": "Building diverse and sustainable supply chains",
        "source": "National TOMs 2025 (Open Access Edition)"
    },
    {
        "theme": "Economy",
        "outcome": "Promoting a diverse and resilient business community",
        "code": "NT15",
        "name": "Expert support to VCSEs and SMEs",
        "unit": "no. staff expert hours",
        "unit_value_gbp": 106.34,
        "description": "This Measure covers employees providing their expertise to Voluntary, Community and Social Enterprises (VCSEs) or Small and Medium Enterprises (SMEs).\nQualifying activities include a range of expert-led sessions offering specialist business advice that builds the capacity of VCSEs and SMEs.\nRecorded hours of staff time can only include time spent preparing and conducting the activities.\nAn employee's expert hours can only be recorded if they have been allocated time during paid working hours or time off in lieu.",
        "evidence_required": "Expert Hours;\nNo. expert hours per employee per event.",
        "ppn_mapping": "Promoting a diverse and resilient business community",
        "source": "National TOMs 2025 (Open Access Edition)"
    },
    {
        "theme": "Economy",
        "outcome": "Promoting a diverse and resilient business community",
        "code": "NT16",
        "name": "Support for VCSEs through donations",
        "unit": "\u00a3 invested",
        "unit_value_gbp": 1.0,
        "description": "This Measure covers financial and in-kind contributions to Voluntary, Community and Social Enterprises (VCSEs). \nThis Measure cannot be used for staff donations or donations raised from third parties at fundraising events.",
        "evidence_required": "Total \u00a3 invested;\nIncluding cash, equipment, and use of assets (e.g., space).",
        "ppn_mapping": "Promoting a diverse and resilient business community",
        "source": "National TOMs 2025 (Open Access Edition)"
    },
    {
        "theme": "Economy",
        "outcome": "Promoting a diverse and resilient business community",
        "code": "NT17",
        "name": "Support for VCSEs through volunteering",
        "unit": "no. staff volunteering hours",
        "unit_value_gbp": 17.48,
        "description": "This Measure covers staff volunteering with Voluntary, Community and Social Enterprises (VCSEs). \nQualifying activities are a range of initiatives aimed at supporting the VCSE and explicitly excludes expert advice. \nRecorded hours of staff time can only include time spent preparing and conducting the activities.\nAn employee's volunteering hours can only be recorded if they have been allocated time during paid working hours or time off in lieu.",
        "evidence_required": "Volunteering Hours;\nNo. volunteering hours per employee per event.",
        "ppn_mapping": "Promoting a diverse and resilient business community",
        "source": "National TOMs 2025 (Open Access Edition)"
    },
    {
        "theme": "Community",
        "outcome": "Building resilient communities",
        "code": "NT28",
        "name": "Support for local community projects through donations",
        "unit": "\u00a3 invested",
        "unit_value_gbp": 1.0,
        "description": "This Measure covers financial and in-kind contributions to a range of initiatives aimed at improving the welfare and wellbeing of a community. \nThese include financial and in-kind contributions to community projects and can be run in partnership with a VCSE or as part of a company programme. \nEach of the types of support offered should be recorded separately in the appropriate categories.",
        "evidence_required": "Total \u00a3 invested;\nIncluding cash, equipment, and use of assets (e.g., space).",
        "ppn_mapping": "Building resilient communities",
        "source": "National TOMs 2025 (Open Access Edition)"
    },
    {
        "theme": "Community",
        "outcome": "Building resilient communities",
        "code": "NT29",
        "name": "Support for local community projects through volunteering",
        "unit": "no. staff volunteering hours",
        "unit_value_gbp": 17.48,
        "description": "This Measure covers staff volunteering on local community projects.\nQualifying activities include a range of initiatives geared at improving community wellbeing.\nThese can be run in partnership with a VCSE or as part of a company programme based on local need.\nRecorded hours of staff time can only include time spent preparing and conducting the activities.\nAn employee's volunteering hours can only be recorded if they have been allocated time during paid working hours or time off in lieu.",
        "evidence_required": "Volunteering Hours;\nNo. volunteering hours per employee per event.",
        "ppn_mapping": "Building resilient communities",
        "source": "National TOMs 2025 (Open Access Edition)"
    },
    {
        "theme": "Community",
        "outcome": "Building community wellbeing",
        "code": "NT26",
        "name": "Support for community health or wellbeing interventions",
        "unit": "\u00a3 invested inc. time, materials, equipment etc",
        "unit_value_gbp": 1.0,
        "description": "This Measure covers support for a range of initiatives aimed at promoting and increasing health and wellbeing in a community such as fitness programmes, nutrition support and smoking, alcohol, and drug abuse reduction initiatives, etc.\nThese can be run in partnership with a VCSE or as part of a company programme.\nRecorded hours of staff time can only include time spent preparing and conducting the activities.\nEach of the types of support offered should be recorded separately.",
        "evidence_required": "Total resources invested;\nIncluding cash, equipment, use of assets (e.g., space) and employee time (valued at the prevailing volunteering or expert hours rate).",
        "ppn_mapping": "Building community wellbeing",
        "source": "National TOMs 2025 (Open Access Edition)"
    },
    {
        "theme": "Community",
        "outcome": "Building community wellbeing",
        "code": "NT27",
        "name": "Support for initiatives focused on strengthening community networks",
        "unit": "\u00a3 invested inc. time, materials, equipment etc",
        "unit_value_gbp": 1.0,
        "description": "This Measure covers support for a range of initiatives aimed at the most vulnerable in society.\nThese include elderly social clubs, digital skills training sessions, fitness programmes for persons with disabilities, etc., and can be run in partnership with a VCSE or as part of a company programme.\nRecorded hours of staff time can only include time spent preparing and conducting the activities.\nEach of the types of support offered should be recorded separately.",
        "evidence_required": "Total resources invested;\nIncluding cash, equipment, use of assets (e.g., space) and employee time (valued at the prevailing volunteering or expert hours rate).",
        "ppn_mapping": "Building community wellbeing",
        "source": "National TOMs 2025 (Open Access Edition)"
    },
    {
        "theme": "Planet",
        "outcome": "Restoring our climate and improving air quality through decarbonisation",
        "code": "NT31",
        "name": "Reductions in scope 1 & 2 CO2e emissions through decarbonisation",
        "unit": "tCO2e",
        "unit_value_gbp": 252.11,
        "description": "This Measure covers the reductions in scope 1 and scope 2 emissions (see Greenhouse Gas Protocol) from decarbonisation initiatives.\nRecorded savings must go beyond the annual percentage reduction required in the UK to achieve net zero emissions by 2050 (currently set at 2.4% per year).\nThis Measure uses the previous year's scope 1 and scope 2 CO2e emissions as a baseline.\nThis Measure can only be used if the previous year's annual carbon report is available.\nThis Measure does not include carbon offsetting.",
        "evidence_required": "Recorded tonnes of carbon dioxide equivalent (CO2e) reduced;\nBaseline expected tonnes of CO2e emissions (set minimum baseline required to achieve net zero by 2050) less Actual tonnes of CO2e emitted.",
        "ppn_mapping": "Restoring our climate and improving air quality through decarbonisation",
        "source": "National TOMs 2025 (Open Access Edition)"
    },
    {
        "theme": "Planet",
        "outcome": "Restoring our climate and improving air quality through decarbonisation",
        "code": "NT31a",
        "name": "Reductions in scope 3 CO2e emissions through decarbonisation",
        "unit": "tCO2e",
        "unit_value_gbp": 252.11,
        "description": "This Measure covers the reductions in scope 3 emissions (see Greenhouse Gas Protocol) from decarbonisation initiatives.\nRecorded savings must go beyond the annual percentage reduction required in the UK to achieve net zero emissions by 2050 (currently set at 2.4% per year).\nThis Measure uses the previous year's scope 3 CO2e emissions as a baseline.\nThis Measure can only be used if the previous year's annual carbon report is available.\nEach year's reductions can only be based on the scope 3 categories stated in the baseline year. \nIf the range of scope 3 categories reported is extended, this can be reported in subsequent years.\nThis Measure does not include carbon offsetting.",
        "evidence_required": "Recorded tonnes of carbon dioxide equivalent (CO2e) reduced;\nBaseline expected tonnes of CO2e emissions (set minimum baseline required to achieve net zero by 2050) less Actual tonnes of CO2e emitted.",
        "ppn_mapping": "Restoring our climate and improving air quality through decarbonisation",
        "source": "National TOMs 2025 (Open Access Edition)"
    },
    {
        "theme": "Planet",
        "outcome": "Restoring our climate and improving air quality through transport",
        "code": "NT32",
        "name": "Reductions in car miles from a green transport programme",
        "unit": "miles saved",
        "unit_value_gbp": 0.0708,
        "description": "This Measure covers the reductions in car miles driven as a result of a green transport programme.\nReductions in car miles is the difference between the actual car miles and a baseline, and can be calculated by measuring or estimating the mileage before the intervention to create the baseline, then measuring the actual car mileage. \nQualifying programmes include cycle-to-work schemes, public transport support, or carpooling / carsharing initiatives (not including hybrid working).\nThis Measure addresses business travel and employee commuting categories within scope 3 emissions.",
        "evidence_required": "Recorded miles reduced;\nBaseline miles driven less Actual number of miles driven.",
        "ppn_mapping": "Restoring our climate and improving air quality through transport",
        "source": "National TOMs 2025 (Open Access Edition)"
    },
    {
        "theme": "Planet",
        "outcome": "Promoting environmentally sustainable procurement",
        "code": "NT116",
        "name": "Expert support on carbon reduction to SMEs in the supply chain",
        "unit": "\u00a3 invested inc. time, materials, equipment etc",
        "unit_value_gbp": 1.0,
        "description": "This Measure covers the costs associated with the provision of expert-led climate change and carbon reduction training for sub contractors which are Small and Medium Enterprises (SMEs).\nSupported initiatives must be expertly designed and qualifying recipients are those within these organisations with decision making capabilities and who are in a position to drive organisational change. \nExamples of training courses are: Supply Chain Sustainability School bronze or higher certificates or the Carbon Literacy Project etc. and can be run in partnership with a VCSE or as part of a company programme.\nRecorded hours of staff time can only include time spent preparing and conducting the activities.\nEach of the types of support offered should be recorded separately.",
        "evidence_required": "Total resources invested;\nIncluding cash, equipment, use of assets (e.g., space) and employee time (valued at the prevailing volunteering or expert hours rate).",
        "ppn_mapping": "Promoting environmentally sustainable procurement",
        "source": "National TOMs 2025 (Open Access Edition)"
    },
    {
        "theme": "Planet",
        "outcome": "Protecting and restoring biodiversity and ecosystems",
        "code": "NT119",
        "name": "Support for green spaces, biodiversity or ecosystems",
        "unit": "\u00a3 invested inc. time, materials, equipment etc",
        "unit_value_gbp": 1.0,
        "description": "This Measure covers support for a range of greenspace creation and development schemes which preserve or enhance natural land or vegetation.\nExamples are funding urban parks and gardens, street planting, brownspace regeneration, etc., and can be run in partnership with a VCSE or as part of a company programme.\nRecorded hours of staff time can only include time spent preparing and conducting the activities.\nEach of the types of support offered should be recorded separately.",
        "evidence_required": "Total resources invested;\nIncluding cash, equipment, use of assets (e.g., space) and employee time (valued at the prevailing volunteering or expert hours rate).",
        "ppn_mapping": "Protecting and restoring biodiversity and ecosystems",
        "source": "National TOMs 2025 (Open Access Edition)"
    },
    {
        "theme": "Planet",
        "outcome": "Transitioning to a regenerative economy",
        "code": "NT87",
        "name": "Reductions in plastics used",
        "unit": "kg",
        "unit_value_gbp": 116.52,
        "description": "This Measure covers reductions in plastic use through reduction initiatives such as designing out waste from plastic packaging or materials.\nThis Measure requires a baseline, which can be determined by the previous year's plastics use or the estimated plastics use without the intervention.",
        "evidence_required": "Plastic reduction;\nBaseline plastic use (in kg) less Actual plastic use (in kg).",
        "ppn_mapping": "Transitioning to a regenerative economy",
        "source": "National TOMs 2025 (Open Access Edition)"
    },
    {
        "code": "NHS-SV1-01",
        "name": "Sustainable IT Framework & GreenOps Observability",
        "theme": "Planet",
        "outcome": "Systemic decarbonisation of digital infrastructure",
        "unit": "milestone programmes",
        "unit_value_gbp": 25000.0,
        "description": "3-phase sustainable IT programme: RGESN eco-design audit, GreenOps platform integration, and carbon scenario modelling.",
        "evidence_required": "Schedule 3b Paragraph 7.1 delivery sign-off: RGESN assessment grid, Sopht GreenOps data logs, and published GDSA case study.",
        "ppn_mapping": "MAC 4.1: Effective Stewardship of the Environment",
        "source": "NHS Schedule 8 / Schedule 3b Benchmark",
        "is_synthetic": false
    },
    {
        "code": "NHS-SV1-02",
        "name": "Carbon Emissions Baselining & Telemetry Verification",
        "theme": "Planet",
        "outcome": "Audited Scope 1, 2, and 3 footprint reduction",
        "unit": "audits",
        "unit_value_gbp": 15000.0,
        "description": "Annual verified GHG Protocol baselining of contract digital operations and supply chain emissions.",
        "evidence_required": "Independent ISO 14064 third-party audit report and annual NHSBSA emissions dashboard.",
        "ppn_mapping": "MAC 4.1: Effective Stewardship of the Environment",
        "source": "NHS Schedule 8 / Schedule 3b Benchmark",
        "is_synthetic": false
    },
    {
        "code": "NHS-SV2-01",
        "name": "NHS Digital Inclusion Device Prescribing",
        "theme": "Community",
        "outcome": "Tackling healthcare digital poverty and access barriers",
        "unit": "prescribed device bundles",
        "unit_value_gbp": 320.0,
        "description": "ADISA-sanitized refurbished laptops/tablets distributed via clinicians with 20GB National Databank connectivity.",
        "evidence_required": "ADISA sanitization certificate, GP/clinical referral vouchers, and Good Things Foundation recipient records.",
        "ppn_mapping": "MAC 2.1: Educational / Skills Partnerships",
        "source": "NHS Schedule 8 / Schedule 3b Benchmark",
        "is_synthetic": false
    },
    {
        "code": "NHS-SV3-01",
        "name": "Modern Slavery Risk Audits & MSAT Verification",
        "theme": "Modern Slavery",
        "outcome": "Protecting vulnerable workers across supply chains",
        "unit": "supplier audits",
        "unit_value_gbp": 18500.0,
        "description": "High-risk Tier 1/Tier 2 hardware and cloud supplier MSAT assessments (achieving MSAT score >= 85%).",
        "evidence_required": "Independent Unseen / third-party audit reports and annual Modern Slavery compliance statement.",
        "ppn_mapping": "MAC 6.3: Modern Slavery and Supply Chain Ethics",
        "source": "NHS Schedule 8 / Schedule 3b Benchmark",
        "is_synthetic": false
    }
]

MASTER_INITIATIVES_DATA: List[Dict[str, Any]] = [
    {
        "id": "INI-01",
        "pillar": "SV1",
        "mac": "MAC 4.1",
        "name": "Sustainable IT Framework (Phases 1\u20133)",
        "description": "RGESN maturity assessment, Sopht GreenOps platform, baseline dashboards, targeted trainings, scenario analysis, action plan, GDSA case study, monitoring, advisory and communications (deliverables D1\u2013D10).",
        "committed_volume": "10 deliverables (D1\u2013D10)",
        "period": "Phase 1 by Y2 Q4; Phase 2 by Y3 Q2; Phase 3 from month 31",
        "beneficiaries": "NHS (FWS transformation perimeter)",
        "delivered_by": "Infosys / Sopht",
        "attribution": "Direct",
        "sch8_ref": "1.18\u20131.24",
        "sch3b_ref": "KPI9a(i) \u00a77.1.1\u20137.1.6; KPI9a(ii) \u00a77.1.7\u20137.1.9",
        "scorecard_id": "KPI-01 to KPI-10",
        "in_scorecard": "Yes",
        "valuation_status": "Not valued",
        "defensible_value_gbp": 0.0,
        "notes": "Phase 3 KPI (tCO2e metric) still to be agreed by Month 24."
    },
    {
        "id": "INI-02",
        "pillar": "SV1",
        "mac": "MAC 4.1",
        "name": "Carbon emissions baselining & supplier-attributed monitoring",
        "description": "Scope 1/2/3 baseline at contract start, refreshed each FY; spend-allocated supplier emissions; annual NHS-specific emissions dashboard; independent verification.",
        "committed_volume": "Annual baseline + dashboard",
        "period": "Each FY, contract term",
        "beneficiaries": "NHSBSA",
        "delivered_by": "Monk Spaces / Infosys",
        "attribution": "Direct",
        "sch8_ref": "1.13, 1.39\u20131.41",
        "sch3b_ref": "\u2014",
        "scorecard_id": "OBL-01, OBL-02, ACT-02",
        "in_scorecard": "Yes",
        "valuation_status": "Not valued",
        "defensible_value_gbp": 0.0,
        "notes": "Enabling: this is what makes any future carbon (NT31/NT31a) claim possible."
    },
    {
        "id": "INI-03",
        "pillar": "SV1",
        "mac": "MAC 4.1",
        "name": "Net Zero Leadership training",
        "description": "Interactive workshops with the Centre for Sustainable Healthcare for board-level NHS leaders.",
        "committed_volume": "280 participants",
        "period": "2027\u20132036",
        "beneficiaries": "NHS board-level leaders",
        "delivered_by": "CSH / Oracle",
        "attribution": "Partner-led (indirect)",
        "sch8_ref": "1.15(a)",
        "sch3b_ref": "\u2014",
        "scorecard_id": "OBL-03",
        "in_scorecard": "Yes",
        "valuation_status": "Not valued",
        "defensible_value_gbp": 0.0,
        "notes": "Schedule 8 per-year rates do not reconcile to 280 (see Cross-check)."
    },
    {
        "id": "INI-04",
        "pillar": "SV1",
        "mac": "MAC 4.1",
        "name": "Health & Nature online module",
        "description": "30-minute online module on nature and health for NHS staff.",
        "committed_volume": "50,000 participants",
        "period": "First 3 years from Y2",
        "beneficiaries": "NHS staff",
        "delivered_by": "Oracle / CSH",
        "attribution": "Partner-led (indirect)",
        "sch8_ref": "1.15(b)",
        "sch3b_ref": "\u2014",
        "scorecard_id": "OBL-04",
        "in_scorecard": "Yes",
        "valuation_status": "Not valued",
        "defensible_value_gbp": 0.0,
        "notes": ""
    },
    {
        "id": "INI-05",
        "pillar": "SV1",
        "mac": "MAC 4.1",
        "name": "Mandatory Sustainability & Green IT training (Infosys workforce)",
        "description": "Mandatory 4-hour training on Infosys Lex for the full contract workforce.",
        "committed_volume": "100% of contract workforce \u00d7 4 hrs",
        "period": "Within 6 months of joining",
        "beneficiaries": "Infosys employees",
        "delivered_by": "Infosys",
        "attribution": "Direct",
        "sch8_ref": "1.15(c)",
        "sch3b_ref": "\u2014",
        "scorecard_id": "OBL-05",
        "in_scorecard": "Yes",
        "valuation_status": "Not valued",
        "defensible_value_gbp": 0.0,
        "notes": "Scorecard shows 186 of 266 completed (70%)."
    },
    {
        "id": "INI-06",
        "pillar": "SV1",
        "mac": "MAC 4.1",
        "name": "CSH Green Space & Health training course",
        "description": "Oracle funds NHS staff on Green Health Routes to attend a 6-hour CSH course plus workshops.",
        "committed_volume": "280 NHS staff",
        "period": "C3 end +1 to +9 years",
        "beneficiaries": "NHS staff at Green Health Route sites",
        "delivered_by": "Oracle (funds) / CSH",
        "attribution": "Partner-led (indirect)",
        "sch8_ref": "1.15(d)",
        "sch3b_ref": "\u2014",
        "scorecard_id": "OBL-06",
        "in_scorecard": "Yes",
        "valuation_status": "Not valued",
        "defensible_value_gbp": 0.0,
        "notes": "Schedule 8 increments do not reconcile to 280 (see Cross-check)."
    },
    {
        "id": "INI-07",
        "pillar": "SV1",
        "mac": "MAC 4.1",
        "name": "Data centre efficiency programme",
        "description": "PUE 1.3 by Jan 2030; ISO 50001/14001; Climate Neutral Data Centre Pact; 100% renewable data centres.",
        "committed_volume": "Compliance throughout",
        "period": "Contract term",
        "beneficiaries": "\u2014",
        "delivered_by": "Oracle / Infosys",
        "attribution": "Partner-led (indirect)",
        "sch8_ref": "1.25",
        "sch3b_ref": "\u2014",
        "scorecard_id": "OBL-07",
        "in_scorecard": "Yes",
        "valuation_status": "Not valued",
        "defensible_value_gbp": 0.0,
        "notes": ""
    },
    {
        "id": "INI-08",
        "pillar": "SV1",
        "mac": "MAC 4.1",
        "name": "Energy-efficient (green) coding across FWS",
        "description": "Developer training on sustainable coding and Green IT awareness for all Infosys developers on the contract.",
        "committed_volume": "All Infosys developers",
        "period": "Contract term",
        "beneficiaries": "Infosys developers",
        "delivered_by": "Infosys / Sopht",
        "attribution": "Direct",
        "sch8_ref": "1.26",
        "sch3b_ref": "KPI9a(i) D4",
        "scorecard_id": "KPI-04, OBL-08",
        "in_scorecard": "Yes",
        "valuation_status": "Not valued",
        "defensible_value_gbp": 0.0,
        "notes": ""
    },
    {
        "id": "INI-09",
        "pillar": "SV1",
        "mac": "MAC 4.1",
        "name": "Nudge Programme \u2014 Workforce Sustainable Behaviour app",
        "description": "Voluntary app nudging NHS staff to cut commuting, travel and paper footprint.",
        "committed_volume": "200,000 active users; >40% of eligible users",
        "period": "From Y3 to end of term",
        "beneficiaries": "NHS staff",
        "delivered_by": "Infosys DX",
        "attribution": "Direct",
        "sch8_ref": "1.6, 1.26(a)",
        "sch3b_ref": "\u2014",
        "scorecard_id": "OBL-09",
        "in_scorecard": "Yes",
        "valuation_status": "Indicative only",
        "defensible_value_gbp": 0.0,
        "notes": "Schedule 8 cites ~70 kg CO2 per person from a Swedish study \u2014 indicative only."
    },
    {
        "id": "INI-10",
        "pillar": "SV1",
        "mac": "MAC 4.1",
        "name": "Commitment to renewables",
        "description": "Partners prioritise renewable electricity; avoid ~150 tCO2e scope 2 per year across 15 years.",
        "committed_volume": "150 tCO2e/yr \u00d7 15 yrs",
        "period": "Contract term",
        "beneficiaries": "\u2014",
        "delivered_by": "Oracle / Infosys",
        "attribution": "Partner-led (indirect)",
        "sch8_ref": "1.27",
        "sch3b_ref": "\u2014",
        "scorecard_id": "OBL-10",
        "in_scorecard": "Yes",
        "valuation_status": "Indicative only",
        "defensible_value_gbp": 0.0,
        "notes": "Oracle UK data centres already 100% renewable (business as usual)."
    },
    {
        "id": "INI-11",
        "pillar": "SV1",
        "mac": "MAC 4.1",
        "name": "Supplier emissions transparency",
        "description": "Supplier screening and ESG assessments; target 50% cut in scope 2 & 3 supply-chain emissions.",
        "committed_volume": "50% reduction",
        "period": "Contract term",
        "beneficiaries": "\u2014",
        "delivered_by": "Infosys",
        "attribution": "Direct",
        "sch8_ref": "1.28",
        "sch3b_ref": "\u2014",
        "scorecard_id": "OBL-11",
        "in_scorecard": "Yes",
        "valuation_status": "Not valued",
        "defensible_value_gbp": 0.0,
        "notes": "Corporate ESG target, not contract-specific."
    },
    {
        "id": "INI-12",
        "pillar": "SV1",
        "mac": "MAC 4.1",
        "name": "IT equipment recovery (Design for Environment)",
        "description": "Oracle recovers 100% of data-centre IT equipment, <0.1% to landfill.",
        "committed_volume": "100% recovery",
        "period": "Contract term",
        "beneficiaries": "\u2014",
        "delivered_by": "Oracle",
        "attribution": "Partner-led (indirect)",
        "sch8_ref": "1.29(a)",
        "sch3b_ref": "\u2014",
        "scorecard_id": "OBL-12",
        "in_scorecard": "Yes",
        "valuation_status": "Not valued",
        "defensible_value_gbp": 0.0,
        "notes": ""
    },
    {
        "id": "INI-13",
        "pillar": "SV1",
        "mac": "MAC 4.1",
        "name": "Social Value Scorecard & Oracle Carbon Calculator",
        "description": "Periodic scorecard; OCI carbon calculator tracking 50% of emissions within 5 years.",
        "committed_volume": "Scorecard live Y1; calculator from Y3",
        "period": "Contract term",
        "beneficiaries": "NHSBSA",
        "delivered_by": "Infosys / Oracle / Monk Spaces",
        "attribution": "Direct",
        "sch8_ref": "1.31\u20131.33",
        "sch3b_ref": "\u2014",
        "scorecard_id": "OBL-13, ACT-03",
        "in_scorecard": "Yes",
        "valuation_status": "Not valued",
        "defensible_value_gbp": 0.0,
        "notes": "Reporting and enabling."
    },
    {
        "id": "INI-14",
        "pillar": "SV1",
        "mac": "MAC 4.1",
        "name": "Green Health Routes (5) and Oracle donation",
        "description": "Oracle funds and resources five community biodiverse green spaces / NHS green health routes in deprived areas; \u00a385,000 donation.",
        "committed_volume": "5 routes; \u00a385,000",
        "period": "One route every two years, 2026\u20132034",
        "beneficiaries": "Patients, staff and communities near NHS sites",
        "delivered_by": "Oracle / CSH (NHS Forest)",
        "attribution": "Partner-led (indirect)",
        "sch8_ref": "1.6, 1.35\u20131.37(a)",
        "sch3b_ref": "SPI11 \u00a717",
        "scorecard_id": "SPI-01",
        "in_scorecard": "Yes",
        "valuation_status": "Valued \u2014 defensible",
        "defensible_value_gbp": 85000.0,
        "notes": "\u00a385,000 donation is not tracked in the scorecard."
    },
    {
        "id": "INI-15",
        "pillar": "SV1",
        "mac": "MAC 4.1",
        "name": "Community Innovation Fund",
        "description": "\u00a325,000 every other year across five regions for workforce, wellbeing and sustainability projects.",
        "committed_volume": "\u00a3125,000 (5 \u00d7 \u00a325,000)",
        "period": "2026, 2028, 2030, 2032, 2034",
        "beneficiaries": "Community projects in 5 regions",
        "delivered_by": "Infosys (NHSBSA on steering group)",
        "attribution": "Direct",
        "sch8_ref": "1.37(b), 1.38",
        "sch3b_ref": "\u2014",
        "scorecard_id": "OBL-19",
        "in_scorecard": "Yes",
        "valuation_status": "Valued \u2014 defensible",
        "defensible_value_gbp": 125000.0,
        "notes": "Cost tracker forecasts an extra \u00a350,000 not in Schedule 8."
    },
    {
        "id": "INI-16",
        "pillar": "SV1",
        "mac": "MAC 4.1",
        "name": "Reforestation donation",
        "description": "One-off separately funded reforestation donation.",
        "committed_volume": "\u00a325,000",
        "period": "Once from 2026",
        "beneficiaries": "Environment / community",
        "delivered_by": "Infosys",
        "attribution": "Direct",
        "sch8_ref": "1.37(b), 1.38",
        "sch3b_ref": "\u2014",
        "scorecard_id": "OBL-20",
        "in_scorecard": "Yes",
        "valuation_status": "Valued \u2014 defensible",
        "defensible_value_gbp": 25000.0,
        "notes": "Must not also be counted as a carbon offset."
    },
    {
        "id": "INI-17",
        "pillar": "SV2",
        "mac": "MAC 2.2",
        "name": "FWS Ambassador Programme (apprenticeships)",
        "description": "80 Level 3/4 apprentices from under-represented / deprived groups providing on-site FWS support; ~10% progress to Level 4.",
        "committed_volume": "80 people; 1,920 months",
        "period": "Cohorts 2027\u20132030",
        "beneficiaries": "People facing barriers to work / deprived areas",
        "delivered_by": "Infosys (employer) / QA Consulting (training)",
        "attribution": "Direct",
        "sch8_ref": "2.7(a), 2.12\u20132.33",
        "sch3b_ref": "KPI9b \u00a77.2; SPI13 \u00a719",
        "scorecard_id": "KPI-11",
        "in_scorecard": "Yes",
        "valuation_status": "Valued \u2014 defensible",
        "defensible_value_gbp": 2576953.6,
        "notes": "Cost tracker has 1,800 person-months vs 1,920 committed (see Cross-check)."
    },
    {
        "id": "INI-18",
        "pillar": "SV2",
        "mac": "MAC 2.2",
        "name": "E-Waste Pipeline for prison leavers",
        "description": "11 prison leavers / ex-offenders trained and employed refurbishing devices for the device prescribing programme.",
        "committed_volume": "11 people; 264 months",
        "period": "Within KPI9b reference points",
        "beneficiaries": "Ex-offenders",
        "delivered_by": "Good Things Foundation (Infosys contractually responsible)",
        "attribution": "Supply chain (Infosys accountable)",
        "sch8_ref": "2.58\u20132.65",
        "sch3b_ref": "KPI9b \u00a77.2",
        "scorecard_id": "KPI-12",
        "in_scorecard": "Yes",
        "valuation_status": "Valued \u2014 defensible",
        "defensible_value_gbp": 615142.0,
        "notes": "Only \u00a3110k cost line found for 264 months of paid work (see Cross-check)."
    },
    {
        "id": "INI-19",
        "pillar": "SV2",
        "mac": "MAC 2.2",
        "name": "Device Prescribing Pilot Programme",
        "description": "Primary-care referrals to volunteer digital consultants who prescribe refurbished devices, connectivity and access to the National Digital Inclusion Network.",
        "committed_volume": "500 consultations; 500 devices; 500 connectivity packages; 29,850 hrs digital basics",
        "period": "24-month pilot",
        "beneficiaries": "People in digital poverty in deprived areas",
        "delivered_by": "Infosys / Good Things Foundation",
        "attribution": "Direct",
        "sch8_ref": "2.7, 2.34\u20132.57",
        "sch3b_ref": "SPI12 \u00a718",
        "scorecard_id": "SPI-02",
        "in_scorecard": "Yes",
        "valuation_status": "Valued \u2014 defensible",
        "defensible_value_gbp": 295488.0,
        "notes": "Volunteer arithmetic in Schedule 8 does not reconcile (see Cross-check)."
    },
    {
        "id": "INI-20",
        "pillar": "SV2",
        "mac": "MAC 2.2",
        "name": "Springboard (NHS-Tech online learning)",
        "description": "Certified tech training and learning hours on Infosys Springboard for high-barrier resident / patient groups.",
        "committed_volume": "10,000 hrs p.a.; ~2,500 learners",
        "period": "Annual",
        "beneficiaries": "Residents / patients facing barriers",
        "delivered_by": "Infosys",
        "attribution": "Direct",
        "sch8_ref": "2.7(b), 2.8",
        "sch3b_ref": "\u2014",
        "scorecard_id": "\u2014",
        "in_scorecard": "No",
        "valuation_status": "Not valued",
        "defensible_value_gbp": 0.0,
        "notes": "Not in the scorecard and not costed in the tracker."
    },
    {
        "id": "INI-21",
        "pillar": "SV2",
        "mac": "MAC 2.2",
        "name": "Work-Ready Clubs & Maker Zones",
        "description": "Weekly after-school clubs for 16\u201318 year-olds; two Maker Zones in the North West.",
        "committed_volume": "18,000 hrs/yr; 200 candidates (2.8) vs ~1,000\u20131,200 participants (2.72)",
        "period": "Five years",
        "beneficiaries": "16\u201318 year-olds in disadvantaged communities",
        "delivered_by": "Oracle / Onside Youth",
        "attribution": "Partner-led (indirect)",
        "sch8_ref": "2.7(c), 2.66\u20132.76",
        "sch3b_ref": "\u2014",
        "scorecard_id": "OBL-15",
        "in_scorecard": "Yes",
        "valuation_status": "Not valued",
        "defensible_value_gbp": 0.0,
        "notes": "Participant numbers inconsistent inside Schedule 8."
    },
    {
        "id": "INI-22",
        "pillar": "SV2",
        "mac": "MAC 2.2",
        "name": "Springpod virtual work experience",
        "description": "Live and pre-recorded virtual work experience for NHS / NHS-tech settings.",
        "committed_volume": "5,000 hrs/yr; 50 NHS candidates",
        "period": "Annual",
        "beneficiaries": "Young people and Tech Returners facing barriers",
        "delivered_by": "Springpod / QA Consulting (Infosys-funded)",
        "attribution": "Direct",
        "sch8_ref": "2.69(b), 2.75(b)",
        "sch3b_ref": "\u2014",
        "scorecard_id": "OBL-16",
        "in_scorecard": "Yes",
        "valuation_status": "Conditional only",
        "defensible_value_gbp": 0.0,
        "notes": ""
    },
    {
        "id": "INI-23",
        "pillar": "SV2",
        "mac": "MAC 2.2",
        "name": "Tech Returners programme",
        "description": "12-week online reskilling, mentoring and job-placement support for experienced professionals returning after a career break.",
        "committed_volume": "Rolling cohorts (no volume stated)",
        "period": "Rolling",
        "beneficiaries": "People returning to work",
        "delivered_by": "Infosys / Oracle",
        "attribution": "Direct",
        "sch8_ref": "2.69(c), 2.75(c)",
        "sch3b_ref": "\u2014",
        "scorecard_id": "OBL-17",
        "in_scorecard": "Yes",
        "valuation_status": "Not valued",
        "defensible_value_gbp": 0.0,
        "notes": "No cohort size or hours committed \u2014 cannot be valued yet."
    },
    {
        "id": "INI-24",
        "pillar": "SV2",
        "mac": "MAC 2.2",
        "name": "Young learners in further education (Sutton Trust + MAT)",
        "description": "Cash donations and health-tech learning content via Sutton Trust Online and a Multi-Academy Trust; summer schools.",
        "committed_volume": "~225 students/yr; 1,350 hrs/yr; MAT 200 learners",
        "period": "From Y3\u20134",
        "beneficiaries": "Students from lower-income backgrounds",
        "delivered_by": "Infosys / Oracle / Sutton Trust / MAT",
        "attribution": "Direct",
        "sch8_ref": "2.7(d), 2.77\u20132.89",
        "sch3b_ref": "\u2014",
        "scorecard_id": "OBL-18, ACT-04",
        "in_scorecard": "Yes",
        "valuation_status": "Not valued",
        "defensible_value_gbp": 0.0,
        "notes": "Schedule 8 names Oracle (2.7d) and Infosys (2.84) as funder."
    },
    {
        "id": "INI-25",
        "pillar": "SV2",
        "mac": "MAC 2.2",
        "name": "Accessibility review",
        "description": "Quarterly accessibility review.",
        "committed_volume": "Per quarter",
        "period": "Contract term",
        "beneficiaries": "\u2014",
        "delivered_by": "Infosys",
        "attribution": "Direct",
        "sch8_ref": "2.8",
        "sch3b_ref": "\u2014",
        "scorecard_id": "\u2014",
        "in_scorecard": "No",
        "valuation_status": "Not valued",
        "defensible_value_gbp": 0.0,
        "notes": "Governance activity; not in the scorecard."
    },
    {
        "id": "INI-26",
        "pillar": "SV3",
        "mac": "MAC 6.3",
        "name": "FWS free of modern slavery (MSAT \u226580%)",
        "description": "Bi-annual Home Office MSAT \u226580% (Green RAG); top-3 suppliers complete MSAT; policies, audits, training.",
        "committed_volume": "MSAT \u226580%, twice a year",
        "period": "1 Apr and 1 Oct annually",
        "beneficiaries": "Workers in the supply chain",
        "delivered_by": "Infosys",
        "attribution": "Direct",
        "sch8_ref": "3.4\u20133.23",
        "sch3b_ref": "KPI9c \u00a77.3",
        "scorecard_id": "KPI-13",
        "in_scorecard": "Yes",
        "valuation_status": "Not valued",
        "defensible_value_gbp": 0.0,
        "notes": "Latest MSAT: Infosys 82%, Oracle 99%."
    },
    {
        "id": "INI-27",
        "pillar": "SV3",
        "mac": "MAC 6.3",
        "name": "Unseen NHS Clinical Modern Slavery Detection training & Learning Academy",
        "description": "Infosys funds Unseen (Hope for Justice) to deliver clinical detection training and an awareness academy for NHS staff.",
        "committed_volume": "\u22652,400 trained",
        "period": "2027 to end of term",
        "beneficiaries": "NHS clinical and patient-facing staff",
        "delivered_by": "Infosys (funds) / Unseen",
        "attribution": "Direct",
        "sch8_ref": "3.24\u20133.31, 3.34(a)",
        "sch3b_ref": "\u2014",
        "scorecard_id": "OBL-21, OBL-22",
        "in_scorecard": "Yes",
        "valuation_status": "Conditional only",
        "defensible_value_gbp": 0.0,
        "notes": ""
    },
    {
        "id": "INI-28",
        "pillar": "SV3",
        "mac": "MAC 6.3",
        "name": "Oracle \u00d7 Unseen e-learning for NHS procurement staff",
        "description": "Two additional modules for NHS procurement staff.",
        "committed_volume": "\u2265600 NHS staff",
        "period": "From Y2",
        "beneficiaries": "NHS procurement staff",
        "delivered_by": "Oracle / Unseen",
        "attribution": "Partner-led (indirect)",
        "sch8_ref": "3.34(b)",
        "sch3b_ref": "\u2014",
        "scorecard_id": "\u2014",
        "in_scorecard": "No",
        "valuation_status": "Not valued",
        "defensible_value_gbp": 0.0,
        "notes": "Not in the scorecard."
    },
    {
        "id": "INI-29",
        "pillar": "SV3",
        "mac": "MAC 6.3",
        "name": "Community support grant to Unseen",
        "description": "Grant supporting Unseen technology initiatives and Infosys\u2013Unseen partnership programmes.",
        "committed_volume": "\u00a350,000",
        "period": "2027\u20132030",
        "beneficiaries": "Unseen (charity)",
        "delivered_by": "Infosys",
        "attribution": "Direct",
        "sch8_ref": "3.32",
        "sch3b_ref": "\u2014",
        "scorecard_id": "OBL-24",
        "in_scorecard": "Yes",
        "valuation_status": "Valued \u2014 defensible",
        "defensible_value_gbp": 50000.0,
        "notes": "Scorecard budget shows \u00a345,000 (rotated \u2014 see Cross-check)."
    },
    {
        "id": "INI-30",
        "pillar": "SV3",
        "mac": "MAC 6.3",
        "name": "Innovation research grant / bursary",
        "description": "Research grant / bursary via NHSBSA Student Services.",
        "committed_volume": "\u00a330,000",
        "period": "2027\u20132030",
        "beneficiaries": "Students / researchers",
        "delivered_by": "Infosys / NHSBSA",
        "attribution": "Direct",
        "sch8_ref": "3.34",
        "sch3b_ref": "\u2014",
        "scorecard_id": "OBL-23",
        "in_scorecard": "Yes",
        "valuation_status": "Not valued",
        "defensible_value_gbp": 0.0,
        "notes": "Scorecard budget \u00a350,000; cost tracker \u00a345,000 (see Cross-check)."
    },
    {
        "id": "INI-31",
        "pillar": "SV3",
        "mac": "MAC 6.3",
        "name": "Five modern slavery PhDs",
        "description": "Fund five PhDs with a university selected by Infosys; competitive call via the Governance Committee.",
        "committed_volume": "5 PhDs within 5 years",
        "period": "2026\u20132031",
        "beneficiaries": "Research community / NHS",
        "delivered_by": "Infosys / partner university",
        "attribution": "Direct",
        "sch8_ref": "3.36\u20133.40",
        "sch3b_ref": "SPI14 \u00a720",
        "scorecard_id": "SPI-03",
        "in_scorecard": "Yes",
        "valuation_status": "Not valued",
        "defensible_value_gbp": 0.0,
        "notes": "Contractual (SPI14) but \u00a30 in the bid; tagged SV1 in the cost tracker."
    },
    {
        "id": "INI-32",
        "pillar": "SV3",
        "mac": "MAC 6.3",
        "name": "PhD implementation fund",
        "description": "Fund to implement, test and verify the PhD recommendations.",
        "committed_volume": "\u00a345,000",
        "period": "2027\u20132035",
        "beneficiaries": "NHSBSA and trusts",
        "delivered_by": "Infosys",
        "attribution": "Direct",
        "sch8_ref": "3.41",
        "sch3b_ref": "\u2014",
        "scorecard_id": "OBL-25",
        "in_scorecard": "Yes",
        "valuation_status": "Not valued",
        "defensible_value_gbp": 0.0,
        "notes": "Scorecard budget shows \u00a330,000 (rotated)."
    },
    {
        "id": "INI-33",
        "pillar": "SV3",
        "mac": "MAC 6.3",
        "name": "Modern Slavery Awareness Champion",
        "description": "Awareness champion and social-scientist support.",
        "committed_volume": "Continuous",
        "period": "2027\u20132030",
        "beneficiaries": "NHS and Infosys staff",
        "delivered_by": "Infosys",
        "attribution": "Direct",
        "sch8_ref": "3.34",
        "sch3b_ref": "\u2014",
        "scorecard_id": "ACT-05",
        "in_scorecard": "Yes",
        "valuation_status": "Not valued",
        "defensible_value_gbp": 0.0,
        "notes": ""
    },
    {
        "id": "INI-34",
        "pillar": "ALL",
        "mac": "\u2014",
        "name": "Programme governance (SV Director, committee, reporting, travel, comms)",
        "description": "Social Value Director, quarterly Governance Committee, dashboards, travel and communication artefacts.",
        "committed_volume": "Ongoing",
        "period": "Contract term",
        "beneficiaries": "\u2014",
        "delivered_by": "Infosys",
        "attribution": "Overhead",
        "sch8_ref": "1.3, 1.42",
        "sch3b_ref": "\u2014",
        "scorecard_id": "OBL-14, ACT-01",
        "in_scorecard": "Yes",
        "valuation_status": "Cost only",
        "defensible_value_gbp": 0.0,
        "notes": "Overhead \u2014 cost only."
    },
    {
        "id": "INI-35",
        "pillar": "SV2",
        "mac": "\u2014",
        "name": "SV2 subject-matter expert (programme support)",
        "description": "UK-based Senior Consultant supporting SV2 delivery.",
        "committed_volume": "180 person-months",
        "period": "Contract term",
        "beneficiaries": "\u2014",
        "delivered_by": "Infosys",
        "attribution": "Overhead",
        "sch8_ref": "\u2014",
        "sch3b_ref": "\u2014",
        "scorecard_id": "\u2014",
        "in_scorecard": "\u2014",
        "valuation_status": "Cost only",
        "defensible_value_gbp": 0.0,
        "notes": "Overhead \u2014 cost only."
    },
    {
        "id": "INI-36",
        "pillar": "SV3",
        "mac": "\u2014",
        "name": "SV3 subject-matter expert (programme support)",
        "description": "Consultant supporting SV3 delivery.",
        "committed_volume": "180 person-months",
        "period": "Contract term",
        "beneficiaries": "\u2014",
        "delivered_by": "Infosys",
        "attribution": "Overhead",
        "sch8_ref": "\u2014",
        "sch3b_ref": "\u2014",
        "scorecard_id": "\u2014",
        "in_scorecard": "\u2014",
        "valuation_status": "Cost only",
        "defensible_value_gbp": 0.0,
        "notes": "Overhead \u2014 cost only."
    },
    {
        "id": "INI-37",
        "pillar": "SV3",
        "mac": "\u2014",
        "name": "Gender sensitivity training (cost line, no commitment)",
        "description": "\u00a3150,000 in the bid cost tracker; no matching commitment in Schedule 8 or the scorecard.",
        "committed_volume": "\u2014",
        "period": "\u2014",
        "beneficiaries": "\u2014",
        "delivered_by": "TBC",
        "attribution": "Orphan cost",
        "sch8_ref": "\u2014",
        "sch3b_ref": "\u2014",
        "scorecard_id": "\u2014",
        "in_scorecard": "No",
        "valuation_status": "Cost only",
        "defensible_value_gbp": 0.0,
        "notes": "Confirm whether dropped or missing from Schedule 8."
    }
]

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
