class VerificationEngine:

    def evaluate(self, findings, verification_evidence):
        results = []

        for finding in findings:

            if verification_evidence["verified"]:
                status = "POTENTIAL"
                confidence = 0.95
            else:
                status = "UNVERIFIED"
                confidence = 0.60

            results.append({
                "finding": finding,
                "status": status,
                "confidence": confidence,
                "evidence": verification_evidence,
            })

        return results
