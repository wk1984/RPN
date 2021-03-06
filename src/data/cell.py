__author__ = 'huziy'

import numpy as np


class Cell:
    def __init__(self, i = -1, j = -1, flow_dir_value = -1):
        self.previous = []
        self.next = None
        self.i = i
        self.j = j
        self.flow_dir_value = flow_dir_value
        self._number_of_upstream_cells = -1
        pass

    def get_number_of_upstream_cells(self):
        #returns number of upstream cells and sets it to the upstream cells
        if self._number_of_upstream_cells < 0:
            self._number_of_upstream_cells = 1  # account itself
            for acell in self.previous:
                assert isinstance(acell, Cell)
                self._number_of_upstream_cells += acell.get_number_of_upstream_cells()

        return self._number_of_upstream_cells


    def set_next(self, next_cell):
        """
        :type next_cell: Cell
        """
        self.next = next_cell
        if next_cell is not None:
            assert self not in next_cell.previous
            next_cell.previous.append(self)

    def get_upstream_cells(self):
        """
        get all upstream cells of the current cell
        including itself
        """
        res = [self]
        for p in self.previous:
            res.extend(p.get_upstream_cells())
        return res

    def get_ij(self):
        return self.i, self.j

    def is_downstream_for(self, aCell):
        """
        :type aCell: Cell
        """
        current = aCell
        while current is not None:
            current = current.__next__
            if current == self:
                return True
        return False
        pass

    def is_upstream_for(self, aCell):
        pass

def main():
    #TODO: implement
    pass

if __name__ == "__main__":
    main()
    print("Hello world")
  