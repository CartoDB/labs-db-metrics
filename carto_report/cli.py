import logging
import warnings
import os
import argparse
from carto_report.report import Reporter

warnings.filterwarnings('ignore')

def get_log_level(loglevel):
    if loglevel == 'DEBUG':
        return logging.DEBUG
    elif loglevel == 'INFO':
        return logging.INFO
    elif loglevel == 'WARNING':
        return logging.WARNING
    else:
        return logging.ERROR

def parse_arguments():
    # set input arguments
    parser = argparse.ArgumentParser(
        description='CARTO reporting tool')

    parser.add_argument('--user-name','-U', dest='CARTO_USER',
                        default=os.getenv('CARTO_USER'),
                        help='Account user name' +
                        ' (defaults to env variable CARTO_USER)')

    parser.add_argument('--api_key','-a', dest='CARTO_API_KEY',
                        default=os.getenv('CARTO_API_KEY'),
                        help='Api key of the account' +
                        ' (defaults to env variable CARTO_API_KEY)')

    parser.add_argument('--api_url', '-u', type=str, dest='CARTO_API_URL',
                        default=os.getenv('CARTO_API_URL'),
                        help='Set the base URL. For example:' +
                        ' https://username.carto.com/ ' +
                        '(defaults to env variable CARTO_API_URL)')

    parser.add_argument('--organization', '-o', type=str, dest='CARTO_ORG',
                        default=os.getenv('CARTO_ORG'),
                        help='Set the name of the organization' +
                        ' account (defaults to env variable CARTO_ORG)')

    parser.add_argument('--output', type=str, dest='output',
                        default='report.html',
                        help='File path for the report, defaults to report.html')

    parser.add_argument('--quota', '-q', type=int, dest='quota',
                        default=5000,
                        help='LDS quota for the user, defaults to 5000')

    parser.add_argument('--loglevel', '-l', type=str, dest='loglevel',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                        default='ERROR', help='How verbose the output should be, default to the most silent'
                        )

    return parser.parse_args()


def main():
    # Get configuration
    args = parse_arguments()

    # logger (better than print)
    logging.basicConfig(
        level=get_log_level(args.loglevel),
        format=' %(asctime)s - %(name)-18s - %(levelname)-8s %(message)s',
        datefmt='%I:%M:%S %p')
    logger = logging.getLogger('carto_report_cli')

    # Set authentification to CARTO
    if args.CARTO_USER and args.CARTO_API_URL and args.CARTO_API_KEY:
        reporter = Reporter(args.CARTO_USER, args.CARTO_API_URL,
                            args.CARTO_ORG, args.CARTO_API_KEY, args.quota)
        try:
            logger.info(
                'Gathering all the information for {}...'.format(args.CARTO_USER))
            result = reporter.report()
            logger.info('Storing at {}'.format(args.output))
            with open(args.output, 'w') as writer:
                writer.write(result)
            logger.info('Finished!')
        except Exception as e:
            logger.error(e)

    else:
        logger.error(
            'You need to provide valid credentials, run with -h parameter for details')
        import sys
        sys.exit(1)


if __name__ == "__main__":
    main()
