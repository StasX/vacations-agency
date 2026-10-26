from utils.dal import DAL

class LikesLogic:
    def __init__(self):
        self.dal = DAL()

    def like(self, user_id, vacation_id):
        with self.dal.transaction():
            # Lock a stable parent row so concurrent toggles also serialize when no like exists.
            self.dal.get_scalar("SELECT id FROM users WHERE id=%s FOR UPDATE", (user_id,))
            # Check if like already exists
            check_sql = "SELECT COUNT(*) as cnt FROM likes WHERE user_id=%s AND vacation_id=%s"
            result = self.dal.get_scalar(check_sql, (user_id, vacation_id))
        
            if result and result['cnt'] > 0:
                # Like exists, delete it
                sql = "DELETE FROM likes WHERE user_id=%s AND vacation_id=%s"
                params = (user_id, vacation_id)
                return self.dal.delete(sql, params)
            else:
                # Like doesn't exist, insert it
                sql = "INSERT INTO likes (user_id, vacation_id) VALUES (%s, %s)"
                params = (user_id, vacation_id)
                return self.dal.insert(sql, params)
