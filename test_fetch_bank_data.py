import unittest

from fetch_bank_data import BASE_URL, output_path_for, parse_env


class FetchBankDataTests(unittest.TestCase):
    def test_reads_sectors_api_key_from_env_file_content(self):
        self.assertEqual(
            parse_env("# comment\nSECTORS_API_KEY = \"example-key\"\n"),
            {"SECTORS_API_KEY": "example-key"},
        )

    def test_creates_one_json_path_per_bank(self):
        self.assertEqual(output_path_for("BBCA").as_posix(), "data/BBCA.json")

    def test_uses_sectors_v2_api_base(self):
        self.assertEqual(BASE_URL, "https://api.sectors.app/v2")


if __name__ == "__main__":
    unittest.main()
