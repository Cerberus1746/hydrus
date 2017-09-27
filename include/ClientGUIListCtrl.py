import ClientConstants as CC
import ClientData
import ClientGUICommon
import HydrusExceptions
import wx
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin
from wx.lib.mixins.listctrl import ColumnSorterMixin

class SaneListCtrl( wx.ListCtrl, ListCtrlAutoWidthMixin, ColumnSorterMixin ):
    
    def __init__( self, parent, height, columns, delete_key_callback = None, activation_callback = None ):
        
        num_columns = len( columns )
        
        wx.ListCtrl.__init__( self, parent, style = wx.LC_REPORT )
        ListCtrlAutoWidthMixin.__init__( self )
        ColumnSorterMixin.__init__( self, num_columns )
        
        self.itemDataMap = {}
        self._data_indices_to_sort_indices = {}
        self._data_indices_to_sort_indices_dirty = False
        self._next_data_index = 0
        
        resize_column = 1
        
        for ( i, ( name, width ) ) in enumerate( columns ):
            
            self.InsertColumn( i, name, width = width )
            
            if width == -1:
                
                resize_column = i + 1
                
            
        
        self.setResizeColumn( resize_column )
        
        self.SetMinSize( ( -1, height ) )
        
        self._delete_key_callback = delete_key_callback
        self._activation_callback = activation_callback
        
        self.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        self.Bind( wx.EVT_LIST_ITEM_ACTIVATED, self.EventItemActivated )
        
        self.Bind( wx.EVT_LIST_COL_BEGIN_DRAG, self.EventBeginColDrag )
        
    
    _GetDataIndex = wx.ListCtrl.GetItemData
    
    def _GetIndexFromDataIndex( self, data_index ):
        
        if self._data_indices_to_sort_indices_dirty:
            
            self._data_indices_to_sort_indices = { self._GetDataIndex( index ) : index for index in range( self.GetItemCount() ) }
            
            self._data_indices_to_sort_indices_dirty = False
            
        
        try:
            
            return self._data_indices_to_sort_indices[ data_index ]
            
        except KeyError:
            
            raise HydrusExceptions.DataMissing( 'Data not found!' )
            
        
    
    def Append( self, display_tuple, sort_tuple ):
        
        index = wx.ListCtrl.Append( self, display_tuple )
        
        data_index = self._next_data_index
        
        self.SetItemData( index, data_index )
        
        self.itemDataMap[ data_index ] = list( sort_tuple )
        self._data_indices_to_sort_indices[ data_index ] = index
        
        self._next_data_index += 1
        
    
    def DeleteItem( self, *args, **kwargs ):
        
        wx.ListCtrl.DeleteItem( self, *args, **kwargs )
        
        self._data_indices_to_sort_indices_dirty = True
        
    
    def EventBeginColDrag( self, event ):
        
        # resizeCol is not zero-indexed
        
        if event.GetColumn() == self._resizeCol - 1:
            
            last_column = self.GetColumnCount()
            
            if self._resizeCol != last_column:
                
                self.setResizeColumn( last_column )
                
            else:
                
                event.Veto()
                
                return
                
            
        
        event.Skip()
        
    
    def EventItemActivated( self, event ):
        
        if self._activation_callback is not None:
            
            self._activation_callback()
            
        else:
            
            event.Skip()
            
        
    
    def EventKeyDown( self, event ):
        
        ( modifier, key ) = ClientData.ConvertKeyEventToSimpleTuple( event )
        
        if key in CC.DELETE_KEYS:
            
            if self._delete_key_callback is not None:
                
                self._delete_key_callback()
                
            
        elif key in ( ord( 'A' ), ord( 'a' ) ) and modifier == wx.ACCEL_CTRL:
            
            self.SelectAll()
            
        else:
            
            event.Skip()
            
        
    
    def GetAllSelected( self ):
        
        indices = []
        
        i = self.GetFirstSelected()
        
        while i != -1:
            
            indices.append( i )
            
            i = self.GetNextSelected( i )
            
        
        return indices
        
    
    def GetClientData( self, index = None ):
        
        if index is None:
            
            data_indicies = [ self._GetDataIndex( index ) for index in range( self.GetItemCount() ) ]
            
            datas = [ tuple( self.itemDataMap[ data_index ] ) for data_index in data_indicies ]
            
            return datas
            
        else:
            
            data_index = self._GetDataIndex( index )
            
            return tuple( self.itemDataMap[ data_index ] )
            
        
    
    def GetIndexFromClientData( self, data, column_index = None ):
        
        for index in range( self.GetItemCount() ):
            
            client_data = self.GetClientData( index )
            
            if column_index is None:
                
                comparison_data = client_data
                
            else:
                
                comparison_data = client_data[ column_index ]
                
            
            if comparison_data == data:
                
                return index
                
            
        
        raise HydrusExceptions.DataMissing( 'Data not found!' )
        
    
    def GetSecondarySortValues( self, col, key1, key2 ):
        
        # This overrides the ColumnSortedMixin. Just spam the whole tuple back.
        
        return ( self.itemDataMap[ key1 ], self.itemDataMap[ key2 ] )
        
    
    def GetListCtrl( self ):
        
        return self
        
    
    def GetSelectedClientData( self ):
        
        indices = self.GetAllSelected()
        
        results = []
        
        for index in indices:
            
            results.append( self.GetClientData( index ) )
            
        
        return results
        
    
    def HasClientData( self, data, column_index = None ):
        
        try:
            
            index = self.GetIndexFromClientData( data, column_index )
            
            return True
            
        except HydrusExceptions.DataMissing:
            
            return False
            
        
    
    def OnSortOrderChanged( self ):
        
        self._data_indices_to_sort_indices_dirty = True
        
    
    def RemoveAllSelected( self ):
        
        indices = self.GetAllSelected()
        
        self.RemoveIndices( indices )
        
    
    def RemoveIndices( self, indices ):
        
        indices.sort()
        
        indices.reverse() # so we don't screw with the indices of deletees below
        
        for index in indices:
            
            self.DeleteItem( index )
            
        
    
    def SelectAll( self ):
        
        currently_selected = set( self.GetAllSelected() )
        
        currently_not_selected = [ index for index in range( self.GetItemCount() ) if index not in currently_selected ]
        
        for index in currently_not_selected:
            
            self.Select( index )
            
        
    
    def UpdateRow( self, index, display_tuple, sort_tuple ):
        
        column = 0
        
        for value in display_tuple:
            
            self.SetStringItem( index, column, value )
            
            column += 1
            
        
        data_index = self._GetDataIndex( index )
        
        self.itemDataMap[ data_index ] = list( sort_tuple )
        
    
class SaneListCtrlForSingleObject( SaneListCtrl ):
    
    def __init__( self, *args, **kwargs ):
        
        # this could one day just take column parameters that the user can pick
        # it could just take obj in append or whatever and generate column tuples off that
        
        self._data_indices_to_objects = {}
        self._objects_to_data_indices = {}
        
        SaneListCtrl.__init__( self, *args, **kwargs )
        
    
    def Append( self, display_tuple, sort_tuple, obj ):
        
        self._data_indices_to_objects[ self._next_data_index ] = obj
        self._objects_to_data_indices[ obj ] = self._next_data_index
        
        SaneListCtrl.Append( self, display_tuple, sort_tuple )
        
    
    def GetIndexFromObject( self, obj ):
        
        try:
            
            data_index = self._objects_to_data_indices[ obj ]
            
            index = self._GetIndexFromDataIndex( data_index )
            
            return index
            
        except KeyError:
            
            raise HydrusExceptions.DataMissing( 'Data not found!' )
            
        
    
    def GetObject( self, index ):
        
        data_index = self._GetDataIndex( index )
        
        return self._data_indices_to_objects[ data_index ]
        
    
    def GetObjects( self, only_selected = False ):
        
        if only_selected:
            
            indicies = self.GetAllSelected()
            
        else:
            
            indicies = range( self.GetItemCount() )
            
        
        data_indicies = [ self._GetDataIndex( index ) for index in indicies ]
        
        datas = [ self._data_indices_to_objects[ data_index ] for data_index in data_indicies ]
        
        return datas
        
    
    def HasObject( self, obj ):
        
        try:
            
            index = self.GetIndexFromObject( obj )
            
            return True
            
        except HydrusExceptions.DataMissing:
            
            return False
            
        
    
    def SetNonDupeName( self, obj ):
        
        # when column population is handled here, we can tuck this into normal append/update calls internally
        
        name = obj.GetName()
        
        current_names = { o.GetName() for o in self.GetObjects() if o is not obj }
        
        if name in current_names:
            
            i = 1
            
            original_name = name
            
            while name in current_names:
                
                name = original_name + ' (' + str( i ) + ')'
                
                i += 1
                
            
            obj.SetName( name )
            
        
    
    def UpdateRow( self, index, display_tuple, sort_tuple, obj ):
        
        SaneListCtrl.UpdateRow( self, index, display_tuple, sort_tuple )
        
        data_index = self._GetDataIndex( index )
        
        self._data_indices_to_objects[ data_index ] = obj
        self._objects_to_data_indices[ obj ] = data_index
        
    
class SaneListCtrlPanel( wx.Panel ):
    
    def __init__( self, parent ):
        
        wx.Panel.__init__( self, parent )
        
        self._vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._buttonbox = wx.BoxSizer( wx.HORIZONTAL )
        
        self._listctrl = None
        
        self._button_infos = []
        
    
    def _SomeSelected( self ):
        
        return self._listctrl.GetSelectedItemCount() > 0
        
    
    def _UpdateButtons( self ):
        
        for ( button, enabled_check_func ) in self._button_infos:
            
            if enabled_check_func():
                
                button.Enable()
                
            else:
                
                button.Disable()
                
            
        
    
    def AddButton( self, label, clicked_func, enabled_only_on_selection = False, enabled_check_func = None ):
        
        button = ClientGUICommon.BetterButton( self, label, clicked_func )
        
        self._buttonbox.AddF( button, CC.FLAGS_VCENTER )
        
        if enabled_only_on_selection:
            
            enabled_check_func = self._SomeSelected
            
        
        if enabled_check_func is not None:
            
            self._button_infos.append( ( button, enabled_check_func ) )
            
        
    
    def AddWindow( self, window ):
        
        self._buttonbox.AddF( window, CC.FLAGS_VCENTER )
        
    
    def EventContentChanged( self, event ):
        
        self._UpdateButtons()
        
        event.Skip()
        
    
    def EventSelectionChanged( self, event ):
        
        self._UpdateButtons()
        
        event.Skip()
        
    
    def SetListCtrl( self, listctrl ):
        
        self._listctrl = listctrl
        
        self._vbox.AddF( self._listctrl, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        self._vbox.AddF( self._buttonbox, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( self._vbox )
        
        self._listctrl.Bind( wx.EVT_LIST_ITEM_SELECTED, self.EventSelectionChanged )
        self._listctrl.Bind( wx.EVT_LIST_ITEM_DESELECTED, self.EventSelectionChanged )
        
        self._listctrl.Bind( wx.EVT_LIST_INSERT_ITEM, self.EventContentChanged )
        self._listctrl.Bind( wx.EVT_LIST_DELETE_ITEM, self.EventContentChanged )
        self._listctrl.Bind( wx.EVT_LIST_DELETE_ALL_ITEMS, self.EventContentChanged )
        
    
class BetterListCtrl( wx.ListCtrl, ListCtrlAutoWidthMixin ):
    
    def __init__( self, parent, name, height_num_chars, sizing_column_initial_width_num_chars, columns, data_to_tuples_func, delete_key_callback = None, activation_callback = None ):
        
        wx.ListCtrl.__init__( self, parent, style = wx.LC_REPORT )
        ListCtrlAutoWidthMixin.__init__( self )
        
        self._data_to_tuples_func = data_to_tuples_func
        
        self._sort_column = 0
        self._sort_asc = True
        
        # eventually have it look up 'name' in some options somewhere and see previous height, width, and column selection
        # this thing should deal with missing entries but also have some filtered defaults for subs listctrl, which will have a bunch of possible columns
        
        self._indices_to_data_info = {}
        self._data_to_indices = {}
        
        ( total_width, height ) = ClientData.ConvertTextToPixels( self, ( sizing_column_initial_width_num_chars, height_num_chars ) )
        
        resize_column = 1
        
        for ( i, ( name, width_num_chars ) ) in enumerate( columns ):
            
            if width_num_chars == -1:
                
                width = -1
                
                resize_column = i + 1
                
            else:
                
                width = ClientData.ConvertTextToPixelWidth( self, width_num_chars )
                
                total_width += width
                
            
            self.InsertColumn( i, name, width = width )
            
        
        self.setResizeColumn( resize_column )
        
        self.SetInitialSize( ( total_width, height ) )
        
        self._delete_key_callback = delete_key_callback
        self._activation_callback = activation_callback
        
        self.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        self.Bind( wx.EVT_LIST_ITEM_ACTIVATED, self.EventItemActivated )
        
        self.Bind( wx.EVT_LIST_COL_BEGIN_DRAG, self.EventBeginColDrag )
        self.Bind( wx.EVT_LIST_COL_CLICK, self.EventColumnClick )
        
    
    def _AddDataInfo( self, data_info ):
        
        ( data, display_tuple, sort_tuple ) = data_info
        
        index = self.Append( display_tuple )
        
        self._indices_to_data_info[ index ] = data_info
        self._data_to_indices[ data ] = index
        
    
    def _GetSelected( self ):
        
        indices = []
        
        i = self.GetFirstSelected()
        
        while i != -1:
            
            indices.append( i )
            
            i = self.GetNextSelected( i )
            
        
        return indices
        
    
    def _RecalculateIndicesAfterDelete( self ):
        
        indices_and_data_info = list( self._indices_to_data_info.items() )
        
        indices_and_data_info.sort()
        
        self._indices_to_data_info = {}
        self._data_to_indices = {}
        
        for ( index, ( old_index, data_info ) ) in enumerate( indices_and_data_info ):
            
            ( data, display_tuple, sort_tuple ) = data_info
            
            self._data_to_indices[ data ] = index
            self._indices_to_data_info[ index ] = data_info
            
        
    
    def _SortDataInfo( self ):
        
        data_infos = list( self._indices_to_data_info.values() )
        
        def sort_key( data_info ):
            
            ( data, display_tuple, sort_tuple ) = data_info
            
            return ( sort_tuple[ self._sort_column ], sort_tuple ) # add the sort tuple to get secondary sorting
            
        
        data_infos.sort( key = sort_key, reverse = not self._sort_asc )
        
        return data_infos
        
    
    def _SortAndRefreshRows( self ):
        
        selected_data_quick = set( self.GetData( only_selected = True ) )
        
        selected_indices = self._GetSelected()
        
        for selected_index in selected_indices:
            
            self.Select( selected_index, False )
            
        
        sorted_data_info = self._SortDataInfo()
        
        self._indices_to_data_info = {}
        self._data_to_indices = {}
        
        for ( index, data_info ) in enumerate( sorted_data_info ):
            
            self._indices_to_data_info[ index ] = data_info
            
            ( data, display_tuple, sort_tuple ) = data_info
            
            self._data_to_indices[ data ] = index
            
            self._UpdateRow( index, display_tuple )
            
            if data in selected_data_quick:
                
                self.Select( index )
                
            
        
    
    def _UpdateRow( self, index, display_tuple ):
        
        for ( column_index, value ) in enumerate( display_tuple ):
            
            self.SetStringItem( index, column_index, value )
            
        
    
    def AddDatas( self, datas ):
        
        for data in datas:
            
            ( display_tuple, sort_tuple ) = self._data_to_tuples_func( data )
            
            self._AddDataInfo( ( data, display_tuple, sort_tuple ) )
            
        
    
    def DeleteDatas( self, datas ):
        
        deletees = [ ( self._data_to_indices[ data ], data ) for data in datas ]
        
        deletees.sort( reverse = True )
        
        for ( index, data ) in deletees:
            
            self.DeleteItem( index )
            
            del self._data_to_indices[ data ]
            
            del self._indices_to_data_info[ index ]
            
        
        self._RecalculateIndicesAfterDelete()
        
        
    
    def DeleteSelected( self ):
        
        indices = self._GetSelected()
        
        indices.sort( reverse = True )
        
        for index in indices:
            
            ( data, display_tuple, sort_tuple ) = self._indices_to_data_info[ index ]
            
            self.DeleteItem( index )
            
            del self._data_to_indices[ data ]
            
            del self._indices_to_data_info[ index ]
            
        
        self._RecalculateIndicesAfterDelete()
        
    
    def EventBeginColDrag( self, event ):
        
        # resizeCol is not zero-indexed
        
        if event.GetColumn() == self._resizeCol - 1:
            
            last_column = self.GetColumnCount()
            
            if self._resizeCol != last_column:
                
                self.setResizeColumn( last_column )
                
            else:
                
                event.Veto()
                
                return
                
            
        
        event.Skip()
        
    
    def EventColumnClick( self, event ):
        
        col = event.GetColumn()
        
        if col == self._sort_column:
            
            self._sort_asc = not self._sort_asc
            
        else:
            
            self._sort_column = col
            
            self._sort_asc = True
            
        
        self._SortAndRefreshRows()
        
    
    def EventItemActivated( self, event ):
        
        if self._activation_callback is not None:
            
            self._activation_callback()
            
        else:
            
            event.Skip()
            
        
    
    def EventKeyDown( self, event ):
        
        ( modifier, key ) = ClientData.ConvertKeyEventToSimpleTuple( event )
        
        if key in CC.DELETE_KEYS:
            
            if self._delete_key_callback is not None:
                
                self._delete_key_callback()
                
            
        elif key in ( ord( 'A' ), ord( 'a' ) ) and modifier == wx.ACCEL_CTRL:
            
            self.SelectAll()
            
        else:
            
            event.Skip()
            
        
    
    def GetData( self, only_selected = False ):
        
        if only_selected:
            
            indices = self._GetSelected()
            
        else:
            
            indices = self._indices_to_data_info.keys()
            
        
        result = []
        
        for index in indices:
            
            ( data, display_tuple, sort_tuple ) = self._indices_to_data_info[ index ]
            
            result.append( data )
            
        
        return result
        
    
    def HasData( self, data ):
        
        return data in self._data_to_indices
        
    
    def HasSelected( self ):
        
        return self.GetSelectedItemCount() > 0
        
    
    def SelectAll( self ):
        
        currently_selected = set( self._GetSelected() )
        
        currently_not_selected = [ index for index in range( self.GetItemCount() ) if index not in currently_selected ]
        
        for index in currently_not_selected:
            
            self.Select( index )
            
        
    
    def SetData( self, datas ):
        
        datas = set( datas )
        existing_datas = set( self._data_to_indices.keys() )
        
        datas_to_add = datas.difference( existing_datas )
        datas_to_update = datas.intersection( existing_datas )
        datas_to_delete = existing_datas.difference( datas )
        
        if len( datas_to_delete ) > 0:
            
            self.DeleteDatas( datas_to_delete )
            
        
        if len( datas_to_update ) > 0:
            
            self.UpdateDatas( datas_to_update )
            
        
        if len( datas_to_add ) > 0:
            
            self.AddDatas( datas_to_add )
            
            self._SortAndRefreshRows()
            
        
    
    def Sort( self, col = None, asc = None ):
        
        if col is not None:
            
            self._sort_column = col
            
        
        if asc is not None:
            
            self._sort_asc = asc
            
        
        self._SortAndRefreshRows()
        
    
    def UpdateDatas( self, datas = None ):
        
        if datas is None:
            
            datas = list( self._data_to_indices.keys() )
            
        
        for data in datas:
            
            ( display_tuple, sort_tuple ) = self._data_to_tuples_func( data )
            
            data_info = ( data, display_tuple, sort_tuple )
            
            index = self._data_to_indices[ data ]
            
            if data_info != self._indices_to_data_info[ index ]:
                
                self._indices_to_data_info[ index ] = data_info
                
                self._UpdateRow( index, display_tuple )
                
            
        

class BetterListCtrlPanel( wx.Panel ):
    
    def __init__( self, parent ):
        
        wx.Panel.__init__( self, parent )
        
        self._vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._buttonbox = wx.BoxSizer( wx.HORIZONTAL )
        
        self._listctrl = None
        
        self._button_infos = []
        
    
    def _HasSelected( self ):
        
        return self._listctrl.HasSelected()
        
    
    def _UpdateButtons( self ):
        
        for ( button, enabled_check_func ) in self._button_infos:
            
            if enabled_check_func():
                
                button.Enable()
                
            else:
                
                button.Disable()
                
            
        
    
    def AddButton( self, label, clicked_func, enabled_only_on_selection = False, enabled_check_func = None ):
        
        button = ClientGUICommon.BetterButton( self, label, clicked_func )
        
        self._buttonbox.AddF( button, CC.FLAGS_VCENTER )
        
        if enabled_only_on_selection:
            
            enabled_check_func = self._HasSelected
            
        
        if enabled_check_func is not None:
            
            self._button_infos.append( ( button, enabled_check_func ) )
            
        
    
    def AddWindow( self, window ):
        
        self._buttonbox.AddF( window, CC.FLAGS_VCENTER )
        
    
    def EventContentChanged( self, event ):
        
        self._UpdateButtons()
        
        event.Skip()
        
    
    def EventSelectionChanged( self, event ):
        
        self._UpdateButtons()
        
        event.Skip()
        
    
    def SetListCtrl( self, listctrl ):
        
        self._listctrl = listctrl
        
        self._vbox.AddF( self._listctrl, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        self._vbox.AddF( self._buttonbox, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( self._vbox )
        
        self._listctrl.Bind( wx.EVT_LIST_ITEM_SELECTED, self.EventSelectionChanged )
        self._listctrl.Bind( wx.EVT_LIST_ITEM_DESELECTED, self.EventSelectionChanged )
        
        self._listctrl.Bind( wx.EVT_LIST_INSERT_ITEM, self.EventContentChanged )
        self._listctrl.Bind( wx.EVT_LIST_DELETE_ITEM, self.EventContentChanged )
        self._listctrl.Bind( wx.EVT_LIST_DELETE_ALL_ITEMS, self.EventContentChanged )
        
    
