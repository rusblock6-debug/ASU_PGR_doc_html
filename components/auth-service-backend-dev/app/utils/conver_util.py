def row_to_dict(row):
    return {column_name: getattr(row, column_name) for column_name in row._fields}
