import {createQuery} from '@rocicorp/zero/solid';

const todos = createQuery(() => {
  let issueQuery = z.query.issue
    .related('creator')
    .related('labels')
    .limit(100);
  const userID = selectedUserID();

  if (userID) {
    issueQuery = issueQuery.where('creatorID', '=', userID);
  }
  return issueQuery;
});




