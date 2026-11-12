"""Recognize an exact historical server footer, never arbitrary editorial edits."""
from app.research.writing import Draft,Citation,validate_draft,StopRun


def saved_draft_matches(article,saved,policy):
    links=policy.get('internal_links',[])[:5]
    modern='\n\n## Para seguir aprendiendo\n\n'+'\n'.join(f'- [{label}]({path})' for label,path in links)
    legacy='\n\n'+'\n\n'.join(f'[{label}]({path})' for label,path in links)
    for key in ['evidence','proposal']:
        if not saved.get(key):continue
        try:
            data=validate_draft(Draft.model_validate(saved[key]),saved['evidence_catalogue'],[],policy,
                metadata_refs=[Citation.model_validate(r) for r in saved.get('reviewed_metadata_evidence',[])],provisional=True).model_dump(mode='json')
        except (ValueError,KeyError,StopRun):continue
        if any(getattr(article,k)!=v for k,v in data.items() if k!='body'):continue
        if article.body==data['body']:return True
        if links and modern in data['body'] and article.body==data['body'].replace(modern,legacy,1):return True
    return False
