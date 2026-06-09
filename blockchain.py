import hashlib
import json
from datetime import datetime
from database import get_db_connection, fetchone_dict, fetchall_dict


class BlockchainService:
    @staticmethod
    def calculate_hash(block_index, timestamp, election_id, candidate_id, voter_hash, previous_hash):
        block_data = {
            "block_index": block_index,
            "timestamp": timestamp,
            "election_id": election_id,
            "candidate_id": candidate_id,
            "voter_hash": voter_hash,
            "previous_hash": previous_hash
        }

        block_string = json.dumps(block_data, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    @staticmethod
    def hash_voter(user_id, election_id):
        raw_data = f"{user_id}-{election_id}"
        return hashlib.sha256(raw_data.encode()).hexdigest()

    @staticmethod
    def get_last_block():
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT TOP 1 *
            FROM blocks
            ORDER BY block_index DESC
        """)

        block = fetchone_dict(cursor)

        conn.close()
        return block

    @staticmethod
    def create_vote_block(election_id, candidate_id, user_id):
        conn = get_db_connection()
        cursor = conn.cursor()

        last_block = BlockchainService.get_last_block()

        if last_block is None:
            block_index = 1
            previous_hash = "0"
        else:
            block_index = last_block["block_index"] + 1
            previous_hash = last_block["current_hash"]

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        voter_hash = BlockchainService.hash_voter(user_id, election_id)

        current_hash = BlockchainService.calculate_hash(
            block_index,
            timestamp,
            election_id,
            candidate_id,
            voter_hash,
            previous_hash
        )

        cursor.execute("""
            INSERT INTO blocks (
                block_index,
                timestamp,
                election_id,
                candidate_id,
                voter_hash,
                previous_hash,
                current_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            block_index,
            timestamp,
            election_id,
            candidate_id,
            voter_hash,
            previous_hash,
            current_hash
        ))

        conn.commit()
        conn.close()

        return {
            "block_index": block_index,
            "timestamp": timestamp,
            "election_id": election_id,
            "candidate_id": candidate_id,
            "voter_hash": voter_hash,
            "previous_hash": previous_hash,
            "current_hash": current_hash
        }

    @staticmethod
    def validate_chain():
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM blocks
            ORDER BY block_index ASC
        """)

        blocks = fetchall_dict(cursor)

        conn.close()

        if len(blocks) == 0:
            return True, "Blockchain chưa có block nào."

        for i in range(len(blocks)):
            block = blocks[i]

            recalculated_hash = BlockchainService.calculate_hash(
                block["block_index"],
                block["timestamp"],
                block["election_id"],
                block["candidate_id"],
                block["voter_hash"],
                block["previous_hash"]
            )

            if block["current_hash"] != recalculated_hash:
                return False, f"Block #{block['block_index']} đã bị thay đổi dữ liệu."

            if i > 0:
                previous_block = blocks[i - 1]

                if block["previous_hash"] != previous_block["current_hash"]:
                    return False, f"Block #{block['block_index']} không liên kết đúng với block trước."

        return True, "Blockchain hợp lệ. Dữ liệu chưa bị thay đổi."