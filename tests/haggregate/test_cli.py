import datetime as dt
import textwrap
from unittest import TestCase
from unittest.mock import MagicMock, patch

from click.testing import CliRunner, Result

from haggregate import RegularizationMode, cli


class CliUsageErrorTestCase(TestCase):
    result: Result

    def setUp(self) -> None:
        runner = CliRunner()
        self.result = runner.invoke(cli.main, [])

    def test_exit_code(self) -> None:
        self.assertTrue(self.result.exit_code > 0)

    def test_error_message(self) -> None:
        self.assertIn("Usage: main [OPTIONS] CONFIGFILE", self.result.output)


class CliConfigFileNotFoundTestCase(TestCase):
    result: Result

    def setUp(self) -> None:
        runner = CliRunner()
        self.result = runner.invoke(cli.main, ["/nonexistent/nonexistent"])

    def test_exit_code(self) -> None:
        self.assertTrue(self.result.exit_code > 0)

    def test_error_message(self) -> None:
        self.assertIn("No such file or directory", self.result.output)


class CliNoTimeSeriesErrorTestCase(TestCase):
    result: Result

    def setUp(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("config.ini", "w") as f:
                f.write(
                    textwrap.dedent(
                        """\
                        [General]
                        target_step = D
                        min_count = 10
                        missing_flag = MISSING
                        """
                    )
                )
            self.result = runner.invoke(cli.main, ["config.ini"])

    def test_exit_code(self) -> None:
        self.assertTrue(self.result.exit_code > 0)

    def test_error_messages(self) -> None:
        self.assertIn("No time series have been specified", self.result.output)


class CliMixin:
    configuration: str
    result: Result
    mock_aggregate: MagicMock
    mock_regularize: MagicMock
    mock_htimeseries: MagicMock

    @patch("haggregate.cli.HTimeseries", return_value="my timeseries")
    @patch("haggregate.cli.regularize", return_value="regularized timeseries")
    @patch("haggregate.cli.aggregate")
    def _execute(
        self,
        mock_aggregate: MagicMock,
        mock_regularize: MagicMock,
        mock_htimeseries: MagicMock,
    ) -> None:
        self.mock_aggregate = mock_aggregate
        self.mock_regularize = mock_regularize
        self.mock_htimeseries = mock_htimeseries
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("config.ini", "w") as f:
                f.write(self.configuration)
            open("mytimeseries.hts", "a").close()
            self.result = runner.invoke(cli.main, ["config.ini"])


class CliTestCase(CliMixin, TestCase):
    configuration = textwrap.dedent(
        """\
        [General]
        target_step = D
        min_count = 10
        missing_flag = MISSING

        [MyTimeseries]
        source_file = mytimeseries.hts
        target_file = aggregatedtimeseries.hts
        method = sum
        """
    )

    def setUp(self) -> None:
        self._execute()

    def test_exit_code(self) -> None:
        self.assertEqual(self.result.exit_code, 0)

    def test_read_source_file(self) -> None:
        self.assertEqual(self.mock_htimeseries.call_count, 1)

    def test_htimeseries_called_correctly(self) -> None:
        self.mock_htimeseries.assert_called_once()
        self.assertEqual(
            self.mock_htimeseries.call_args[1],
            {"format": self.mock_htimeseries.FILE, "default_tzinfo": dt.timezone.utc},
        )

    def test_regularize_called_correctly(self) -> None:
        self.mock_regularize.assert_called_once_with(
            "my timeseries",
            new_date_flag="DATEINSERT",
            mode=RegularizationMode.INTERVAL,
        )

    def test_aggregate_called_correctly(self) -> None:
        self.mock_aggregate.assert_called_once_with(
            "regularized timeseries",
            "D",
            "sum",
            min_count=10,
            missing_flag="MISSING",
            target_timestamp_offset=None,
        )

    def test_wrote_target_file(self) -> None:
        self.assertEqual(self.mock_aggregate.return_value.write.call_count, 1)


class RegularizationModeTestCase(CliMixin, TestCase):
    def _run(self, method: str) -> None:
        self.configuration = textwrap.dedent(
            f"""\
            [General]
            target_step = D
            min_count = 10
            missing_flag = MISSING

            [MyTimeseries]
            source_file = mytimeseries.hts
            target_file = aggregatedtimeseries.hts
            method = {method}
            """
        )
        self._execute()

    def test_regularize_called_correctly_when_sum(self) -> None:
        self._run("sum")
        self.mock_regularize.assert_called_once_with(
            "my timeseries",
            new_date_flag="DATEINSERT",
            mode=RegularizationMode.INTERVAL,
        )

    def test_regularize_called_correctly_when_mean(self) -> None:
        self._run("mean")
        self.mock_regularize.assert_called_once_with(
            "my timeseries",
            new_date_flag="DATEINSERT",
            mode=RegularizationMode.INSTANTANEOUS,
        )

    def test_regularize_called_correctly_when_max(self) -> None:
        self._run("max")
        self.mock_regularize.assert_called_once_with(
            "my timeseries",
            new_date_flag="DATEINSERT",
            mode=RegularizationMode.INTERVAL,
        )

    def test_regularize_called_correctly_when_min(self) -> None:
        self._run("min")
        self.mock_regularize.assert_called_once_with(
            "my timeseries",
            new_date_flag="DATEINSERT",
            mode=RegularizationMode.INTERVAL,
        )


class CliWithTargetTimestampOffsetTestCase(CliMixin, TestCase):
    configuration = textwrap.dedent(
        """\
        [General]
        target_step = D
        target_timestamp_offset = 1min
        min_count = 10
        missing_flag = MISSING

        [MyTimeseries]
        source_file = mytimeseries.hts
        target_file = aggregatedtimeseries.hts
        method = sum
        """
    )

    def setUp(self) -> None:
        self._execute()

    def test_exit_code(self) -> None:
        self.assertEqual(self.result.exit_code, 0)

    def test_read_source_file(self) -> None:
        self.assertEqual(self.mock_htimeseries.call_count, 1)

    def test_regularize_called_correctly(self) -> None:
        self.mock_regularize.assert_called_once_with(
            "my timeseries",
            new_date_flag="DATEINSERT",
            mode=RegularizationMode.INTERVAL,
        )

    def test_aggregate_called_correctly(self) -> None:
        self.mock_aggregate.assert_called_once_with(
            "regularized timeseries",
            "D",
            "sum",
            min_count=10,
            missing_flag="MISSING",
            target_timestamp_offset="1min",
        )

    def test_wrote_target_file(self) -> None:
        self.assertEqual(self.mock_aggregate.return_value.write.call_count, 1)
