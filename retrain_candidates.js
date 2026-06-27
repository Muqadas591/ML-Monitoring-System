def low_confidence_alert(confidence):
    if confidence < 0.5:
        return True
    return False