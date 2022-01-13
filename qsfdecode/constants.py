from enum import Enum

class StringEnum(Enum):

    def __str__(self):
        return self.value

class Format(StringEnum):
    CSV = 'csv'
    JSON = 'json'
    NDJSON = 'ndjson'
    SPSS = 'spss'
    TSV = 'tsv'
    XML = 'xml'
    TXT = 'text'
    XLSX = 'xslx'

    def __str__(self):
        return self.value


class TimeZones(StringEnum):
    PAC_MIDWAY = 'Pacific/Midway'
    PAC_HONOLULU = 'Pacific/Honolulu'
    AMR_ANC = 'America/Anchorage'
    AMR_LAX = 'America/Los_Angeles'
    AMR_PHX = 'America/Phoenix'
    AMR_DNV = 'America/Denver'
    CAN_E_SKT = 'Canada/East-Saskatchewan'
    AMR_CHI = 'America/Chicago'
    AMR_RIO = 'America/Rio_Branco'
    AMR_NYC = 'America/New_York'
    CAN_ATL = 'Canada/Atlantic'
    AMR_LAPAZ = 'America/La_Paz'
    CAN_NEWF = 'Canada/Newfoundland'
    AMR_MVDO = 'America/Montevideo'
    AMR_ABE = 'America/Argentina/Buenos_Aires'
    AMR_NORONHA = 'America/Noronha'
    ATLANTIC_AZORES = 'Atlantic/Azores'
    ATLANTIC_CVRD = 'Atlantic/Cape_Verde'
    ATLANTIC_REYK = 'Atlantic/Reykjavik'
    EUR_LONDON = 'Europe/London'
    EUR_BERLIN = 'Europe/Berlin'
    AFR_BANGUI = 'Africa/Bangui'
    EUR_ATHENS = 'Europe/Athens'
    AFR_HARARE = 'Africa/Harare'
    EUR_MOSCOW = 'Europe/Moscow' 
    AFR_NAIR = 'Africa/Nairobi'
    ASI_TEHRAN = 'Asia/Tehran'
    ASI_MUSCAT = 'Asia/Muscat'
    ASI_BAKU = 'Asia/Baku'
    ASI_KABUL = 'Asia/Kabul'
    ASI_YEKAT = 'Asia/Yekaterinburg'
    ASI_KARACHI = 'Asia/Karachi'
    ASI_CALCUTTA = 'Asia/Calcutta'
    ASI_KATMANDU = 'Asia/Katmandu'
    ASI_DHAKA = 'Asia/Dhaka'
    ASI_NOVO = 'Asia/Novosibirsk'
    ASI_RANGOON = 'Asia/Rangoon'
    ASI_KRASNOYK = 'Asia/Krasnoyk'
    ASI_YAKUTSK = 'Asia/Yakutsk'
    ASI_SEOUL = 'Asia/Seoul'
    AUS_DAARSK = 'Australia/Daarsk'
    ASI_BANGKORWIN = 'Asia/Bangkorwin'
    AUS_ADELAIDE = 'Australia/Adelaide'
    AUS_BRISBANE = 'Australia/Brisbane'
    AUS_CANBERRA = 'Australia/Canberra'
    ASI_MAGADAN = 'Asia/Magadan'
    PAC_AUCKLAND = 'Pacific/Auckland'
    PAC_FIJU = 'Pacific/Fiji'
    PAC_TONGATAPU = 'Pacific/Tongatapu'