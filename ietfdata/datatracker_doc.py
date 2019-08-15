from ietfdata.datatracker import *
from plotly.offline import plot
import plotly.graph_objs as go
import plotly.figure_factory as ff
import matplotlib.pyplot as plt
import datetime
import dateutil.parser
import pandas as pd
import numpy as np
import random

data = DataTracker()


def get_area():
    """
        This function returns the names of ietf_areas
        Other attributes of the areas can be gotten using the v.attribute_name
    """
    for area in data.ietf_area():
        print(area.name)


def get_active_wg_area():
    """
        This function gets the names of all active working groups in a particular area
        IDs for the area needs to be known to use this function.

        IETF AREAS (ACRONYMS)                                            ID
        Routing(rtg)                                                     1249
        Internet(int)                                                    1052
        Application and real-time(art)                                   2010
        General(gen)                                                     1008
        Operations & Management(ops)                                     1193
        Security(sec)                                                    1260
        Transport(tsv)                                                   1324
    """
    area_list = []
    for active_area in data.active_wg_area("1249"):
        area_list.append(active_area.name)

    area_list.sort()

    # for i in range(len(area_list)):
    #     print(area_list[i])

    return area_list


def get_document_bes():
    bes_doc = []
    doc_expires = []
    expires = []
    doc_submissions = []
    submit_date = []
    bes_result = []
    size = 20

    for doc in data.area_group_document("1960", "draft", "1"):
        bes_doc.append(doc.title)
        doc_expires.append(doc.expires)
        doc_submissions.append(doc.submissions[0])

    # for i in range(len(doc_names)):
    #     print

    for d in range(len(doc_expires)):
        result = dateutil.parser.parse(doc_expires[d]).date()
        y = result.strftime('%Y-%m-%d')
        expires.append(y)

    for submission in range(len(doc_submissions)):
        for j in data.submission(doc_submissions[submission]):
            submit_date.append(j.submission_date)

    for i in range(size):
        temp = [bes_doc[i], expires[i], submit_date[i]]
        bes_result.append(temp)

    return bes_result


def get_document_brp():
    brp_doc = []
    doc_expires = []
    expires = []
    doc_submissions = []
    submit_date = []
    bes_result = []

    for doc in data.area_group_document("2150", "draft", "1"):
        brp_doc.append(doc.title)
        doc_expires.append(doc.expires)
        doc_submissions.append(doc.submissions[0])

    # for i in range(len(doc_names)):
    #     print

    for d in range(len(doc_expires)):
        result = dateutil.parser.parse(doc_expires[d]).date()
        y = result.strftime('%Y-%m-%d')
        expires.append(y)

    for submission in range(len(doc_submissions)):
        for j in data.submission(doc_submissions[submission]):
            submit_date.append(j.submission_date)

    for i in range(len(brp_doc)):
        temp = [brp_doc[i], expires[i], submit_date[i]]
        bes_result.append(temp)

    return bes_result


def get_document_bfd():
    bfd_doc = []
    doc_expires = []
    expires = []
    doc_submissions = []
    submit_date = []
    bes_result = []

    for doc in data.area_group_document("1628", "draft", "1"):
        bfd_doc.append(doc.title)
        doc_expires.append(doc.expires)
        doc_submissions.append(doc.submissions[0])

    for d in range(len(doc_expires)):
        result = dateutil.parser.parse(doc_expires[d]).date()
        y = result.strftime('%Y-%m-%d')
        expires.append(y)

    for submission in range(len(doc_submissions)):
        for j in data.submission(doc_submissions[submission]):
            submit_date.append(j.submission_date)

    for i in range(len(bfd_doc)):
        temp = [bfd_doc[i], expires[i], submit_date[i]]
        bes_result.append(temp)

    return bes_result


def get_document_bier():
    bier_doc = []
    doc_expires = []
    expires = []
    doc_submissions = []
    submit_date = []
    bes_result = []

    for doc in data.area_group_document("1964", "draft", "1"):
        bier_doc.append(doc.title)
        doc_expires.append(doc.expires)
        doc_submissions.append(doc.submissions[0])

    for d in range(len(doc_expires)):
        result = dateutil.parser.parse(doc_expires[d]).date()
        y = result.strftime('%Y-%m-%d')
        expires.append(y)

    for submission in range(len(doc_submissions)):
        for j in data.submission(doc_submissions[submission]):
            submit_date.append(j.submission_date)

    for i in range(len(bier_doc)):
        temp = [bier_doc[i], expires[i], submit_date[i]]
        bes_result.append(temp)

    return bes_result


def get_document_ccmp():
    ccmp_doc = []
    doc_expires = []
    expires = []
    doc_submissions = []
    submit_date = []
    bes_result = []

    for doc in data.area_group_document("1524", "draft", "1"):
        ccmp_doc.append(doc.title)
        doc_expires.append(doc.expires)
        doc_submissions.append(doc.submissions[0])

    for d in range(len(doc_expires)):
        result = dateutil.parser.parse(doc_expires[d]).date()
        y = result.strftime('%Y-%m-%d')
        expires.append(y)

    for submission in range(len(doc_submissions)):
        for j in data.submission(doc_submissions[submission]):
            submit_date.append(j.submission_date)

    for i in range(len(ccmp_doc)):
        temp = [ccmp_doc[i], expires[i], submit_date[i]]
        bes_result.append(temp)

    return bes_result


def get_document_dnet():
    dnet_doc = []
    doc_expires = []
    expires = []
    doc_submissions = []
    submit_date = []
    bes_result = []

    for doc in data.area_group_document("1962", "draft", "1"):
        dnet_doc.append(doc.title)
        doc_expires.append(doc.expires)
        doc_submissions.append(doc.submissions[0])

    for d in range(len(doc_expires)):
        result = dateutil.parser.parse(doc_expires[d]).date()
        y = result.strftime('%Y-%m-%d')
        expires.append(y)

    for submission in range(len(doc_submissions)):
        for j in data.submission(doc_submissions[submission]):
            submit_date.append(j.submission_date)

    for i in range(len(dnet_doc)):
        temp = [dnet_doc[i], expires[i], submit_date[i]]
        bes_result.append(temp)

    return bes_result


def get_document_idr():
    idr_doc = []
    doc_expires = []
    expires = []
    doc_submissions = []
    submit_date = []
    bes_result = []

    for doc in data.area_group_document("1041", "draft", "1"):
        idr_doc.append(doc.title)
        doc_expires.append(doc.expires)
        doc_submissions.append(doc.submissions[0])

    for d in range(len(doc_expires)):
        result = dateutil.parser.parse(doc_expires[d]).date()
        y = result.strftime('%Y-%m-%d')
        expires.append(y)

    for submission in range(len(doc_submissions)):
        for j in data.submission(doc_submissions[submission]):
            submit_date.append(j.submission_date)

    for i in range(len(idr_doc)):
        temp = [idr_doc[i], expires[i], submit_date[i]]
        bes_result.append(temp)

    return bes_result


def get_document_irs():
    irs_doc = []
    doc_expires = []
    expires = []
    doc_submissions = []
    submit_date = []
    bes_result = []

    for doc in data.area_group_document("1875", "draft", "1"):
        irs_doc.append(doc.title)
        doc_expires.append(doc.expires)
        doc_submissions.append(doc.submissions[0])

    for d in range(len(doc_expires)):
        result = dateutil.parser.parse(doc_expires[d]).date()
        y = result.strftime('%Y-%m-%d')
        expires.append(y)

    for submission in range(len(doc_submissions)):
        for j in data.submission(doc_submissions[submission]):
            submit_date.append(j.submission_date)

    for i in range(len(irs_doc)):
        temp = [irs_doc[i], expires[i], submit_date[i]]
        bes_result.append(temp)

    return bes_result


def get_document_lisp():
    lisp_doc = []
    doc_expires = []
    expires = []
    doc_submissions = []
    submit_date = []
    bes_result = []

    for doc in data.area_group_document("1751", "draft", "1"):
        lisp_doc.append(doc.title)
        doc_expires.append(doc.expires)
        doc_submissions.append(doc.submissions[0])

    for d in range(len(doc_expires)):
        result = dateutil.parser.parse(doc_expires[d]).date()
        y = result.strftime('%Y-%m-%d')
        expires.append(y)

    for submission in range(len(doc_submissions)):
        for j in data.submission(doc_submissions[submission]):
            submit_date.append(j.submission_date)

    for i in range(len(lisp_doc)):
        temp = [lisp_doc[i], expires[i], submit_date[i]]
        bes_result.append(temp)

    return bes_result


def get_document_man():
    man_doc = []
    doc_expires = []
    expires = []
    doc_submissions = []
    submit_date = []
    bes_result = []

    for doc in data.area_group_document("1132", "draft", "1"):
        man_doc.append(doc.title)
        doc_expires.append(doc.expires)
        doc_submissions.append(doc.submissions[0])

    for d in range(len(doc_expires)):
        result = dateutil.parser.parse(doc_expires[d]).date()
        y = result.strftime('%Y-%m-%d')
        expires.append(y)

    for submission in range(len(doc_submissions)):
        for j in data.submission(doc_submissions[submission]):
            submit_date.append(j.submission_date)

    for i in range(len(man_doc)):
        temp = [man_doc[i], expires[i], submit_date[i]]
        bes_result.append(temp)

    return bes_result


def get_document_mls():
    mls_doc = []
    doc_expires = []
    expires = []
    doc_submissions = []
    submit_date = []
    bes_result = []

    for doc in data.area_group_document("1140", "draft", "1"):
        mls_doc.append(doc.title)
        doc_expires.append(doc.expires)
        doc_submissions.append(doc.submissions[0])

    for d in range(len(doc_expires)):
        result = dateutil.parser.parse(doc_expires[d]).date()
        y = result.strftime('%Y-%m-%d')
        expires.append(y)

    for submission in range(len(doc_submissions)):
        for j in data.submission(doc_submissions[submission]):
            submit_date.append(j.submission_date)

    for i in range(len(mls_doc)):
        temp = [mls_doc[i], expires[i], submit_date[i]]
        bes_result.append(temp)

    return bes_result


def get_document_nvo():
    nvo_doc = []
    doc_expires = []
    expires = []
    doc_submissions = []
    submit_date = []
    bes_result = []

    for doc in data.area_group_document("1840", "draft", "1"):
        nvo_doc.append(doc.title)
        doc_expires.append(doc.expires)
        doc_submissions.append(doc.submissions[0])

    for d in range(len(doc_expires)):
        result = dateutil.parser.parse(doc_expires[d]).date()
        y = result.strftime('%Y-%m-%d')
        expires.append(y)

    for submission in range(len(doc_submissions)):
        for j in data.submission(doc_submissions[submission]):
            submit_date.append(j.submission_date)

    for i in range(len(nvo_doc)):
        temp = [nvo_doc[i], expires[i], submit_date[i]]
        bes_result.append(temp)

    return bes_result


def get_document_pce():
    pce_doc = []
    doc_expires = []
    expires = []
    doc_submissions = []
    submit_date = []
    bes_result = []

    for doc in data.area_group_document("1630", "draft", "1"):
        pce_doc.append(doc.title)
        doc_expires.append(doc.expires)
        doc_submissions.append(doc.submissions[0])

    for d in range(len(doc_expires)):
        result = dateutil.parser.parse(doc_expires[d]).date()
        y = result.strftime('%Y-%m-%d')
        expires.append(y)

    for submission in range(len(doc_submissions)):
        for j in data.submission(doc_submissions[submission]):
            submit_date.append(j.submission_date)

    for i in range(len(pce_doc)):
        temp = [pce_doc[i], expires[i], submit_date[i]]
        bes_result.append(temp)

    return bes_result


def get_document_pim():
    pim_doc = []
    doc_expires = []
    expires = []
    doc_submissions = []
    submit_date = []
    bes_result = []

    for doc in data.area_group_document("1397", "draft", "1"):
        pim_doc.append(doc.title)
        doc_expires.append(doc.expires)
        doc_submissions.append(doc.submissions[0])

    for d in range(len(doc_expires)):
        result = dateutil.parser.parse(doc_expires[d]).date()
        y = result.strftime('%Y-%m-%d')
        expires.append(y)

    for submission in range(len(doc_submissions)):
        for j in data.submission(doc_submissions[submission]):
            submit_date.append(j.submission_date)

    for i in range(len(pim_doc)):
        temp = [pim_doc[i], expires[i], submit_date[i]]
        bes_result.append(temp)

    return bes_result


def get_document_pls():
    pls_doc = []
    doc_expires = []
    expires = []
    doc_submissions = []
    submit_date = []
    bes_result = []

    for doc in data.area_group_document("1969", "draft", "1"):
        pls_doc.append(doc.title)
        doc_expires.append(doc.expires)
        doc_submissions.append(doc.submissions[0])

    for d in range(len(doc_expires)):
        result = dateutil.parser.parse(doc_expires[d]).date()
        y = result.strftime('%Y-%m-%d')
        expires.append(y)

    for submission in range(len(doc_submissions)):
        for j in data.submission(doc_submissions[submission]):
            submit_date.append(j.submission_date)

    for i in range(len(pls_doc)):
        temp = [pls_doc[i], expires[i], submit_date[i]]
        bes_result.append(temp)

    return bes_result


def get_document_rawg():
    rawg_doc = []
    doc_expires = []
    expires = []
    doc_submissions = []
    submit_date = []
    bes_result = []

    for doc in data.area_group_document("1619", "draft", "1"):
        rawg_doc.append(doc.title)
        doc_expires.append(doc.expires)
        doc_submissions.append(doc.submissions[0])

    for d in range(len(doc_expires)):
        result = dateutil.parser.parse(doc_expires[d]).date()
        y = result.strftime('%Y-%m-%d')
        expires.append(y)

    for submission in range(len(doc_submissions)):
        for j in data.submission(doc_submissions[submission]):
            submit_date.append(j.submission_date)

    for i in range(len(rawg_doc)):
        temp = [rawg_doc[i], expires[i], submit_date[i]]
        bes_result.append(temp)

    return bes_result


def get_document_rpn():
    rpn_doc = []
    doc_expires = []
    expires = []
    doc_submissions = []
    submit_date = []
    bes_result = []

    for doc in data.area_group_document("1730", "draft", "1"):
        rpn_doc.append(doc.title)
        doc_expires.append(doc.expires)
        doc_submissions.append(doc.submissions[0])

    for d in range(len(doc_expires)):
        result = dateutil.parser.parse(doc_expires[d]).date()
        y = result.strftime('%Y-%m-%d')
        expires.append(y)

    for submission in range(len(doc_submissions)):
        for j in data.submission(doc_submissions[submission]):
            submit_date.append(j.submission_date)

    for i in range(len(rpn_doc)):
        temp = [rpn_doc[i], expires[i], submit_date[i]]
        bes_result.append(temp)

    return bes_result


def get_document_sfd():
    sfd_doc = []
    doc_expires = []
    expires = []
    doc_submissions = []
    submit_date = []
    bes_result = []

    for doc in data.area_group_document("1910", "draft", "1"):
        sfd_doc.append(doc.title)
        doc_expires.append(doc.expires)
        doc_submissions.append(doc.submissions[0])

    for d in range(len(doc_expires)):
        result = dateutil.parser.parse(doc_expires[d]).date()
        y = result.strftime('%Y-%m-%d')
        expires.append(y)

    for submission in range(len(doc_submissions)):
        for j in data.submission(doc_submissions[submission]):
            submit_date.append(j.submission_date)

    for i in range(len(sfd_doc)):
        temp = [sfd_doc[i], expires[i], submit_date[i]]
        bes_result.append(temp)

    return bes_result


def get_document_sprn():
    sprn_doc = []
    doc_expires = []
    expires = []
    doc_submissions = []
    submit_date = []
    bes_result = []

    for doc in data.area_group_document("1905", "draft", "1"):
        sprn_doc.append(doc.title)
        doc_expires.append(doc.expires)
        doc_submissions.append(doc.submissions[0])

    for d in range(len(doc_expires)):
        result = dateutil.parser.parse(doc_expires[d]).date()
        y = result.strftime('%Y-%m-%d')
        expires.append(y)

    for submission in range(len(doc_submissions)):
        for j in data.submission(doc_submissions[submission]):
            submit_date.append(j.submission_date)

    for i in range(len(sprn_doc)):
        temp = [sprn_doc[i], expires[i], submit_date[i]]
        bes_result.append(temp)

    return bes_result


def get_document_teas():
    teas_doc = []
    doc_expires = []
    expires = []
    doc_submissions = []
    submit_date = []
    bes_result = []

    for doc in data.area_group_document("1985", "draft", "1"):
        teas_doc.append(doc.title)
        doc_expires.append(doc.expires)
        doc_submissions.append(doc.submissions[0])

    for d in range(len(doc_expires)):
        result = dateutil.parser.parse(doc_expires[d]).date()
        y = result.strftime('%Y-%m-%d')
        expires.append(y)

    for submission in range(len(doc_submissions)):
        for j in data.submission(doc_submissions[submission]):
            submit_date.append(j.submission_date)

    for i in range(len(teas_doc)):
        temp = [teas_doc[i], expires[i], submit_date[i]]
        bes_result.append(temp)

    return bes_result


# document = open('document.txt', 'a')

# get_area()
# get_active_wg_area()
# # get_document()
# get_document_expire_date()
# get_submissions_date()

bes = get_document_bes()
# document.write(str(bes) + '\n')

bier = get_document_bier()
# document.write(str(bier) + '\n')

bfd = get_document_bfd()
# document.write(str(bfd) + '\n')

brp = get_document_brp()
# document.write(str(brp) + '\n')

ccmp = get_document_ccmp()
# document.write(str(ccmp) + '\n')

dnet = get_document_dnet()
# document.write(str(dnet) + '\n')

idr = get_document_idr()
# document.write(str(idr) + '\n')

irs = get_document_irs()
# document.write(str(irs) + '\n')

lisp = get_document_lisp()
# document.write(str(lisp) + '\n')

man = get_document_man()
# document.write(str(man) + '\n')

mls = get_document_mls()
# document.write(str(mls) + '\n')

nvo = get_document_nvo()
# document.write(str(nvo) + '\n')

pce = get_document_pce()
# document.write(str(pce) + '\n')

pim = get_document_pim()
# document.write(str(pim) + '\n')

pls = get_document_pls()
# document.write(str(pls) + '\n')

rawg = get_document_rawg()
# document.write(str(rawg) + '\n')

rpn = get_document_rpn()
# document.write(str(rpn) + '\n')

sfd = get_document_sfd()
# document.write(str(sfd) + '\n')

sprn = get_document_sprn()
# document.write(str(sprn) + '\n')

teas = get_document_teas()
# document.write(str(teas) + '\n')
#
# document.close()

group = get_active_wg_area()


# print(group)


def visualization():
    r = lambda: random.randint(0, 255)
    # print('#%02X%02X%02X' % (r(),r(),r()))
    colors = ['#%02X%02X%02X' % (r(), r(), r())]

    df = []
    for doc, start, end in bes:
        list_ = dict(Task=doc, Start=start, Finish=end, Resource=group[0])
        df.append(list_)
        colors.append('#%02X%02X%02X' % (r(), r(), r()))
    for doc, start, end in brp:
        list_ = dict(Task=doc, Start=start, Finish=end, Resource=group[1])
        df.append(list_)
        colors.append('#%02X%02X%02X' % (r(), r(), r()))
    for doc, start, end in bfd:
        list_ = dict(Task=doc, Start=start, Finish=end, Resource=group[2])
        df.append(list_)
        colors.append('#%02X%02X%02X' % (r(), r(), r()))
    for doc, start, end in bier:
        list_ = dict(Task=doc, Start=start, Finish=end, Resource=group[3])
        df.append(list_)
        colors.append('#%02X%02X%02X' % (r(), r(), r()))
    for doc, start, end in ccmp:
        list_ = dict(Task=doc, Start=start, Finish=end, Resource=group[4])
        df.append(list_)
        colors.append('#%02X%02X%02X' % (r(), r(), r()))
    for doc, start, end in dnet:
        list_ = dict(Task=doc, Start=start, Finish=end, Resource=group[5])
        df.append(list_)
        colors.append('#%02X%02X%02X' % (r(), r(), r()))
    for doc, start, end in idr:
        list_ = dict(Task=doc, Start=start, Finish=end, Resource=group[6])
        df.append(list_)
        colors.append('#%02X%02X%02X' % (r(), r(), r()))
    for doc, start, end in irs:
        list_ = dict(Task=doc, Start=start, Finish=end, Resource=group[7])
        df.append(list_)
        colors.append('#%02X%02X%02X' % (r(), r(), r()))
    for doc, start, end in lisp:
        list_ = dict(Task=doc, Start=start, Finish=end, Resource=group[8])
        df.append(list_)
        colors.append('#%02X%02X%02X' % (r(), r(), r()))
    for doc, start, end in man:
        list_ = dict(Task=doc, Start=start, Finish=end, Resource=group[9])
        df.append(list_)
        colors.append('#%02X%02X%02X' % (r(), r(), r()))
    for doc, start, end in mls:
        list_ = dict(Task=doc, Start=start, Finish=end, Resource=group[10])
        df.append(list_)
        colors.append('#%02X%02X%02X' % (r(), r(), r()))
    for doc, start, end in nvo:
        list_ = dict(Task=doc, Start=start, Finish=end, Resource=group[11])
        df.append(list_)
        colors.append('#%02X%02X%02X' % (r(), r(), r()))
    for doc, start, end in pce:
        list_ = dict(Task=doc, Start=start, Finish=end, Resource=group[12])
        df.append(list_)
        colors.append('#%02X%02X%02X' % (r(), r(), r()))
    for doc, start, end in pim:
        list_ = dict(Task=doc, Start=start, Finish=end, Resource=group[13])
        df.append(list_)
        colors.append('#%02X%02X%02X' % (r(), r(), r()))
    for doc, start, end in pls:
        list_ = dict(Task=doc, Start=start, Finish=end, Resource=group[14])
        df.append(list_)
        colors.append('#%02X%02X%02X' % (r(), r(), r()))
    for doc, start, end in rawg:
        list_ = dict(Task=doc, Start=start, Finish=end, Resource=group[15])
        df.append(list_)
        colors.append('#%02X%02X%02X' % (r(), r(), r()))
    for doc, start, end in rpn:
        list_ = dict(Task=doc, Start=start, Finish=end, Resource=group[16])
        df.append(list_)
        colors.append('#%02X%02X%02X' % (r(), r(), r()))
    for doc, start, end in sfd:
        list_ = dict(Task=doc, Start=start, Finish=end, Resource=group[17])
        df.append(list_)
        colors.append('#%02X%02X%02X' % (r(), r(), r()))
    for doc, start, end in sprn:
        list_ = dict(Task=doc, Start=start, Finish=end, Resource=group[18])
        df.append(list_)
        colors.append('#%02X%02X%02X' % (r(), r(), r()))
    for doc, start, end in teas:
        list_ = dict(Task=doc, Start=start, Finish=end, Resource=group[19])
        df.append(list_)
        colors.append('#%02X%02X%02X' % (r(), r(), r()))

    fig = ff.create_gantt(df, colors=colors, index_col='Resource', title='Document Life Span',
                          show_colorbar=True,
                          showgrid_x=True,
                          showgrid_y=True)
    fig['layout'].update(autosize=False, width=1200, height=3000, margin=dict(l=300, pad=10))
    fig.show()


visualization()

# x = ['2000', '2001', '2002', '2003', '2004', '2005', '2006', '2007', '2008', '2009', '2010', '2011', '2012', '2013',
#      '2014', '2015', '2016', '2017', '2018', '2019']
# #
# y_pos = np.arange(len(get_document()))
# #
# plt.barh(y_pos, x)  # get_active_wg_area()
# plt.gcf().autofmt_xdate()
# plt.xlabel("Years")
# plt.ylabel("Groups")
# plt.title('IETF Datatracker')
# plt.yticks(y_pos, get_document())
#
# plt.show()
