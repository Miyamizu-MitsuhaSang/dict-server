XZA_EMAIL_ADDRESS = "3480039769@qq.com"
CYQ_EMAIL_ADDRESS = ""

async def feedback_distribution(report_type:str, receivers: list):
    if report_type == "dict_fr":
        receivers.append(XZA_EMAIL_ADDRESS)
    elif report_type == "dict_jp":
        receivers.append(CYQ_EMAIL_ADDRESS)
    else:
        pass
