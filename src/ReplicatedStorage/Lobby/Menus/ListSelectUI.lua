-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:46 PM
-- Time elapsed: 17 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_6 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_8 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_9 = require(game.ReplicatedStorage.Shared.ListAdapter)
local v_u_10 = require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_15 = {
    ["ListElement"] = {},
    ["get_default_list_ui_obj"] = function(_) --[[ Name: get_default_list_ui_obj ]] --[[ Line: 579 ]]
        return game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.ListSelectUI.Default:Clone();
    end,
    ["get_popup_text_list_ui_obj"] = function(_) --[[ Name: get_popup_text_list_ui_obj ]] --[[ Line: 580 ]]
        return game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.ListSelectUI.PopupText:Clone();
    end,
    ["set_filter_button_fns_list"] = function(_, p11, p12) --[[ Name: set_filter_button_fns_list ]] --[[ Line: 582 ]]
        --[[ Upvalues: (copy 1): v_u_6 ]]
        if p11:get_settings_section_visible() ~= true then
            p11:set_settings_section_visible()
            for _, v13 in p11:get_settings_buttons():key_itr() do
                v13:set_visible(false)
            end;
        end;
        for _ = 1, p12:count() do
            if p11:get_settings_buttons():count() > 0 then
                local v14 = p11:get_settings_buttons():pop_front()
                v14:set_visible(true)
                p12:pop_front()(v14)
            else
                v_u_6:warnf("ListSelectUI:set_filter_button_fns_list - not enough settings buttons for filter button fns list")
            end;
        end;
    end
}
v_u_15.ListElement.new = function(_, p_u_16, p_u_17, p_u_18, p_u_19) --[[ Name: new ]] --[[ Line: 18 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_5, (copy 3): v_u_7, (copy 4): v_u_1 ]]
    local v_u_20 = {}
    local v_u_21 = nil
    local v_u_22 = nil
    v_u_20.get_button = function(_) --[[ Name: get_button ]] --[[ Line: 24 ]]
        --[[ Upvalues: (ref 1): v_u_22 ]]
        return v_u_22;
    end;
    local v_u_23 = nil
    local v_u_24 = nil
    local v_u_25 = nil
    local v_u_26 = nil
    local v_u_27 = nil
    local v_u_28 = -1
    local v_u_29 = -1
    v_u_20.clear_data = function(_) --[[ Name: clear_data ]] --[[ Line: 34 ]]
        --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_28, (ref 3): v_u_29 ]]
        v_u_27 = nil
        v_u_28 = -1
        v_u_29 = -1
    end;
    v_u_20.get_data = function(_) --[[ Name: get_data ]] --[[ Line: 39 ]]
        --[[ Upvalues: (ref 1): v_u_27 ]]
        return v_u_27;
    end;
    v_u_20.get_i_data = function(_) --[[ Name: get_i_data ]] --[[ Line: 40 ]]
        --[[ Upvalues: (ref 1): v_u_28 ]]
        return v_u_28;
    end;
    v_u_20.get_i_display_element = function(_) --[[ Name: get_i_display_element ]] --[[ Line: 41 ]]
        --[[ Upvalues: (ref 1): v_u_29 ]]
        return v_u_29;
    end;
    local v_u_30 = true
    v_u_20.set_enabled = function(p31, p32) --[[ Name: set_enabled ]] --[[ Line: 44 ]]
        --[[ Upvalues: (ref 1): v_u_30 ]]
        v_u_30 = p32
        return p31;
    end;
    local function f_cons() --[[ Name: cons ]] --[[ Line: 49 ]]
        --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_4, (copy 3): p_u_17, (copy 4): p_u_18, (ref 5): v_u_22, (copy 6): p_u_16, (ref 7): v_u_5, (ref 8): v_u_30, (ref 9): v_u_7, (ref 10): v_u_27, (copy 11): v_u_20, (ref 12): v_u_23, (ref 13): v_u_24, (ref 14): v_u_25, (ref 15): v_u_26 ]]
        v_u_21 = v_u_4:new(p_u_17, p_u_17:get_uichild_parent(), p_u_18.MainSurface):set_default_sgui()
        v_u_22 = p_u_17:add_cycle_element(p_u_16, 1, v_u_5:new(v_u_4:new(v_u_21, p_u_18.MainSurface, p_u_18.SelectButton), p_u_16._spui, function() --[[ Line: 54 ]]
            --[[ Upvalues: (ref 1): v_u_30, (ref 2): p_u_16, (ref 3): v_u_7, (ref 4): v_u_27, (ref 5): p_u_17, (ref 6): v_u_20 ]]
            if v_u_30 ~= false then
                p_u_16._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                if v_u_27 ~= nil then
                    p_u_17:on_element_selected(v_u_27, v_u_20)
                end;
            end;
        end))
        v_u_5:button_add_enabled_anim(v_u_22, function() --[[ Line: 63 ]]
            --[[ Upvalues: (ref 1): p_u_17 ]]
            return p_u_17:get_alpha();
        end)
        v_u_23 = p_u_18.MainSurface.SurfaceGui.Frame
        v_u_24 = v_u_23.NameDisplay
        v_u_25 = v_u_23.DescriptionDisplay
        v_u_26 = v_u_23.PlayerIcon
    end;
    v_u_20.get_name_display = function(_) --[[ Name: get_name_display ]] --[[ Line: 71 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        return v_u_24;
    end;
    v_u_20.get_description_display = function(_) --[[ Name: get_description_display ]] --[[ Line: 72 ]]
        --[[ Upvalues: (ref 1): v_u_25 ]]
        return v_u_25;
    end;
    v_u_20.get_icon_display = function(_) --[[ Name: get_icon_display ]] --[[ Line: 73 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        return v_u_26;
    end;
    v_u_20.get_ui_root = function(_) --[[ Name: get_ui_root ]] --[[ Line: 74 ]]
        --[[ Upvalues: (ref 1): v_u_23 ]]
        return v_u_23;
    end;
    v_u_20.set_display_element = function(p33, p34, p35, p36) --[[ Name: set_display_element ]] --[[ Line: 76 ]]
        --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_28, (ref 3): v_u_29, (ref 4): v_u_26, (ref 5): v_u_1, (ref 6): v_u_24, (ref 7): v_u_25, (ref 8): v_u_22, (copy 9): p_u_19, (ref 10): v_u_21 ]]
        v_u_27 = p34
        v_u_28 = p35
        v_u_29 = p36
        v_u_26.Image = v_u_1:transparent_assetid()
        v_u_24.Text = ""
        v_u_25.Text = ""
        if not v_u_27 then
            v_u_22:set_visible(false)
            return p33;
        end;
        v_u_22:set_visible(true)
        p_u_19(v_u_27, v_u_24, v_u_26, v_u_21, p33, p35, p36)
        return p33;
    end;
    v_u_20.set_select_button_text = function(p37, p38) --[[ Name: set_select_button_text ]] --[[ Line: 92 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_22 ]]
        for _, v39 in v_u_1:get_list_of_children_of_classname(v_u_22:get_part(), "TextLabel"):key_itr() do
            v39.Text = p38
        end;
        return p37;
    end;
    v_u_20.set_select_button_enabled = function(p40, p41) --[[ Name: set_select_button_enabled ]] --[[ Line: 99 ]]
        --[[ Upvalues: (ref 1): v_u_22 ]]
        v_u_22:set_enabled(p41)
        return p40;
    end;
    v_u_20.set_visible = function(p42, p43) --[[ Name: set_visible ]] --[[ Line: 104 ]]
        --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_22 ]]
        v_u_21:set_visible(p43)
        v_u_22:set_visible(p43)
        return p42;
    end;
    v_u_20.layout = function(_) --[[ Name: layout ]] --[[ Line: 110 ]]
        --[[ Upvalues: (ref 1): v_u_21 ]]
        v_u_21:layout()
    end;
    f_cons()
    return v_u_20;
end;
v_u_15.new = function(_, p_u_44, p_u_45, p_u_46, p_u_47, p_u_48, p_u_49, p_u_50, p_u_51, p52) --[[ Name: new ]] --[[ Line: 118 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_9, (copy 4): v_u_15, (copy 5): v_u_1, (copy 6): v_u_5, (copy 7): v_u_4, (copy 8): v_u_7, (copy 9): v_u_10, (copy 10): v_u_8 ]]
    local v_u_53 = p52 == nil and {} or p52
    local v_u_54 = v_u_3:new(p_u_45, p_u_46)
    local v_u_55 = nil
    local v_u_56 = nil
    local v_u_57 = nil
    local v_u_58 = nil
    local v_u_59 = nil
    local v_u_60 = nil
    local v_u_61 = nil
    local v_u_62 = nil
    v_u_54.get_ui_root = function(_) --[[ Name: get_ui_root ]] --[[ Line: 143 ]]
        --[[ Upvalues: (ref 1): v_u_62 ]]
        return v_u_62;
    end;
    local v_u_63 = nil
    local v_u_64 = v_u_2:new()
    v_u_54.set_settings_section_visible = function(_) --[[ Name: set_settings_section_visible ]] --[[ Line: 147 ]]
        --[[ Upvalues: (ref 1): v_u_63 ]]
        if v_u_63 then
            v_u_63.Visible = true
        end;
    end;
    v_u_54.get_settings_section_visible = function(_) --[[ Name: get_settings_section_visible ]] --[[ Line: 152 ]]
        --[[ Upvalues: (ref 1): v_u_63 ]]
        if v_u_63 then
            return v_u_63.Visible;
        else
            return false;
        end;
    end;
    v_u_54.get_settings_buttons = function(_) --[[ Name: get_settings_buttons ]] --[[ Line: 160 ]]
        --[[ Upvalues: (copy 1): v_u_64 ]]
        return v_u_64;
    end;
    local v_u_65 = v_u_2:new()
    v_u_54.get_element_list = function(_) --[[ Name: get_element_list ]] --[[ Line: 164 ]]
        --[[ Upvalues: (copy 1): v_u_65 ]]
        return v_u_65;
    end;
    local v_u_66 = nil
    local v_u_75 = v_u_9:new():set_fn_get_data_list(function() --[[ Line: 169 ]]
        --[[ Upvalues: (copy 1): v_u_54 ]]
        return v_u_54:get_element_list();
    end):set_fn_set_element_data(function(p67, p68, p69, p70) --[[ Line: 170 ]]
        if p68 == nil then
            p67:set_visible(false)
            p67:clear_data()
        else
            p67:set_visible(true)
            p67:set_display_element(p68, p69, p70)
        end;
    end):set_fn_next_prev_visible(function(p71, p72) --[[ Line: 179 ]]
        --[[ Upvalues: (ref 1): v_u_56, (ref 2): v_u_57 ]]
        v_u_56:set_visible(p71)
        v_u_57:set_visible(p72)
    end):set_fn_update_page_display(function(p73, p74) --[[ Line: 183 ]]
        --[[ Upvalues: (ref 1): v_u_55, (ref 2): p_u_50, (copy 3): v_u_54 ]]
        if p73 == 1 and p74 == 1 then
            v_u_55.Text = ""
        else
            v_u_55.Text = string.format("%d/%d", p73, p74)
        end;
        if p_u_50 then
            p_u_50(v_u_54, p73, p74)
        end;
    end)
    v_u_54.get_list_adapter = function(_) --[[ Name: get_list_adapter ]] --[[ Line: 194 ]]
        --[[ Upvalues: (copy 1): v_u_75 ]]
        return v_u_75;
    end;
    local v_u_76 = true
    v_u_54.set_enabled = function(p77, p78) --[[ Name: set_enabled ]] --[[ Line: 197 ]]
        --[[ Upvalues: (ref 1): v_u_76, (copy 2): v_u_75 ]]
        v_u_76 = p78
        for _, v79 in v_u_75:get_display_elements():key_itr() do
            v79:set_enabled(p78)
        end;
        return p77;
    end;
    v_u_54.is_enabled = function(_) --[[ Name: is_enabled ]] --[[ Line: 204 ]]
        --[[ Upvalues: (ref 1): v_u_76 ]]
        return v_u_76;
    end;
    local function f_cons() --[[ Name: cons ]] --[[ Line: 206 ]]
        --[[ Upvalues: (ref 1): p_u_51, (ref 2): v_u_15, (ref 3): v_u_1, (copy 4): v_u_54, (ref 5): v_u_62, (ref 6): v_u_55, (ref 7): v_u_59, (ref 8): v_u_60, (ref 9): v_u_61, (ref 10): v_u_63, (ref 11): v_u_2, (ref 12): v_u_53, (copy 13): p_u_44, (ref 14): v_u_5, (ref 15): v_u_4, (ref 16): v_u_7, (copy 17): v_u_64, (copy 18): v_u_75, (ref 19): v_u_56, (copy 20): p_u_45, (ref 21): v_u_76, (ref 22): v_u_57, (copy 23): p_u_46, (copy 24): p_u_49, (ref 25): v_u_58, (ref 26): v_u_66, (copy 27): p_u_48 ]]
        if p_u_51 == nil then
            p_u_51 = v_u_15:get_default_list_ui_obj()
        end;
        p_u_51.Name = v_u_1:gen_name(p_u_51.Name)
        v_u_54:set_showing(true)
        v_u_54._native_size = p_u_51.PrimaryPart.Size
        v_u_54._size = v_u_54._native_size
        v_u_62 = p_u_51.MainSurface.SurfaceGui.Frame
        v_u_55 = v_u_62.PageDisplay
        v_u_59 = v_u_62.Header
        v_u_59.Text = ""
        v_u_60 = v_u_62.Sub
        v_u_60.Text = ""
        v_u_61 = v_u_62.EmptyDisplay
        v_u_63 = v_u_62:FindFirstChild("SettingsSection")
        if v_u_63 then
            v_u_63.Visible = false
        end;
        local v80 = v_u_2:new()
        if v_u_53.SettingsButtonObjs == nil then
            local v81 = p_u_51:FindFirstChild("SettingsItems")
            if v81 then
                local v82 = v_u_2:new()
                for _, v83 in pairs(v81:GetChildren()) do
                    v82:push_back(v83)
                end;
                v82:sort(function(p84, p85) --[[ Line: 240 ]]
                    return p84.Name < p85.Name;
                end)
                v80:push_back_table_list(v82:get_table())
            end;
        else
            v80:push_back_table_list(v_u_53.SettingsButtonObjs)
        end;
        if v80:count() > 0 then
            for _, v86 in v80:key_itr() do
                local v_u_87 = nil
                v_u_87 = v_u_54:add_cycle_element(p_u_44, 1, v_u_5:new(v_u_4:new(v_u_54, p_u_51.PrimaryPart, v86), p_u_44._spui, function() --[[ Line: 253 ]]
                    --[[ Upvalues: (ref 1): p_u_44, (ref 2): v_u_7, (ref 3): v_u_87 ]]
                    p_u_44._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                    if typeof(v_u_87:get_bound_data()) == "function" then
                        v_u_87:get_bound_data()()
                    end;
                end)):set_auto_zoffset_behaviour(true)
                v_u_87:set_visible(false)
                v_u_64:push_back(v_u_87)
            end;
        end;
        v_u_75:set_fn_is_empty(function(p88) --[[ Line: 266 ]]
            --[[ Upvalues: (ref 1): v_u_61 ]]
            v_u_61.Visible = p88
        end)
        v_u_56 = v_u_54:add_cycle_element(p_u_44, 1, v_u_5:new(v_u_4:new(v_u_54, p_u_51.PrimaryPart, p_u_51.ListButtonDown), p_u_45, function() --[[ Line: 273 ]]
            --[[ Upvalues: (ref 1): v_u_76, (ref 2): p_u_44, (ref 3): v_u_7, (ref 4): v_u_75 ]]
            if v_u_76 ~= false then
                p_u_44._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                v_u_75:next_page()
            end;
        end))
        v_u_57 = v_u_54:add_cycle_element(p_u_44, 1, v_u_5:new(v_u_4:new(v_u_54, p_u_51.PrimaryPart, p_u_51.ListButtonUp), p_u_45, function() --[[ Line: 283 ]]
            --[[ Upvalues: (ref 1): v_u_76, (ref 2): p_u_44, (ref 3): v_u_7, (ref 4): v_u_75 ]]
            if v_u_76 ~= false then
                p_u_44._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                v_u_75:prev_page()
            end;
        end))
        v_u_54:add_cycle_element(p_u_44, 1, v_u_5:new(v_u_4:new(v_u_54, p_u_51.PrimaryPart, p_u_51.BackButtonSurface), p_u_45, function() --[[ Line: 293 ]]
            --[[ Upvalues: (ref 1): v_u_76, (ref 2): p_u_44, (ref 3): v_u_7, (ref 4): p_u_46, (ref 5): v_u_54, (ref 6): p_u_49 ]]
            if v_u_76 ~= false then
                p_u_44._sfx_manager:play_sfx(v_u_7.SFX_MENU_CLOSE)
                p_u_46:remove_menu(v_u_54)
                p_u_49(nil, v_u_54, nil)
            end;
        end))
        local v89 = p_u_51:FindFirstChild("InfoButton")
        if v89 then
            v_u_58 = v_u_54:add_cycle_element(p_u_44, 1, v_u_5:new(v_u_4:new(v_u_54, p_u_51.PrimaryPart, v89), p_u_45, function() --[[ Line: 306 ]]
                --[[ Upvalues: (ref 1): v_u_76, (ref 2): p_u_44, (ref 3): v_u_7, (ref 4): v_u_66 ]]
                if v_u_76 ~= false then
                    p_u_44._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                    if v_u_66 then
                        v_u_66()
                    end;
                end;
            end):set_passive_anim(true))
            v_u_58:set_visible(false)
        end;
        local v90 = v_u_2:new()
        if v_u_53.AnchorsObjs == nil then
            local l_Anchors_0 = p_u_51.Anchors
            local v91 = v_u_2:new()
            for _, v92 in pairs(l_Anchors_0:GetChildren()) do
                v91:push_back(v92)
            end;
            v91:sort(function(p93, p94) --[[ Line: 326 ]]
                return p93.Name < p94.Name;
            end)
            v90:push_back_table_list(v91:get_table())
        else
            v90:push_back_table_list(v_u_53.AnchorsObjs)
        end;
        local v95 = p_u_51:FindFirstChild("ListElement")
        v95.Parent = nil
        if v_u_53.ListElementProto ~= nil then
            v95 = v_u_53.ListElementProto
        end;
        v_u_75:create_list_elements_from_anchors_and_proto(v90:get_table(), v95, p_u_51, function(p96) --[[ Line: 343 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): p_u_44, (ref 3): v_u_54, (ref 4): p_u_48 ]]
            return v_u_15.ListElement:new(p_u_44, v_u_54, p96, p_u_48);
        end)
        v_u_54:refresh()
        v_u_54:transition_update_visual(0)
        v_u_54:layout()
    end;
    v_u_54.refresh = function(p97) --[[ Name: refresh ]] --[[ Line: 354 ]]
        --[[ Upvalues: (copy 1): p_u_47 ]]
        p97:get_element_list():clear()
        p_u_47(p97)
        p97:page_update()
    end;
    v_u_54.set_header_text = function(p98, p99) --[[ Name: set_header_text ]] --[[ Line: 360 ]]
        --[[ Upvalues: (ref 1): v_u_59 ]]
        v_u_59.Text = p99
        return p98;
    end;
    v_u_54.set_sub_text = function(p100, p101) --[[ Name: set_sub_text ]] --[[ Line: 365 ]]
        --[[ Upvalues: (ref 1): v_u_60 ]]
        v_u_60.Text = p101
        return p100;
    end;
    local v_u_102 = true
    v_u_54.set_close_on_element_select = function(p103, p104) --[[ Name: set_close_on_element_select ]] --[[ Line: 371 ]]
        --[[ Upvalues: (ref 1): v_u_102 ]]
        v_u_102 = p104
        return p103;
    end;
    v_u_54.on_element_selected = function(p105, p106, p107) --[[ Name: on_element_selected ]] --[[ Line: 376 ]]
        --[[ Upvalues: (copy 1): p_u_49, (ref 2): v_u_102, (copy 3): p_u_46 ]]
        p_u_49(p106, p105, p107)
        if v_u_102 then
            p_u_46:remove_menu(p105)
        end;
    end;
    v_u_54.page_update = function(_) --[[ Name: page_update ]] --[[ Line: 383 ]]
        --[[ Upvalues: (copy 1): v_u_75 ]]
        v_u_75:page_update()
    end;
    v_u_54.set_fn_info_button_pressed = function(p108, p109) --[[ Name: set_fn_info_button_pressed ]] --[[ Line: 387 ]]
        --[[ Upvalues: (ref 1): v_u_58, (ref 2): v_u_66 ]]
        if v_u_58 then
            v_u_58:set_visible(true)
        end;
        v_u_66 = p109
        return p108;
    end;
    v_u_54.set_fn_on_update_page_display = function(p110, p111) --[[ Name: set_fn_on_update_page_display ]] --[[ Line: 395 ]]
        --[[ Upvalues: (ref 1): p_u_50, (copy 2): v_u_75 ]]
        p_u_50 = p111
        v_u_75:page_update()
        return p110;
    end;
    v_u_54.set_empty_message = function(p112, p113) --[[ Name: set_empty_message ]] --[[ Line: 401 ]]
        --[[ Upvalues: (ref 1): v_u_61 ]]
        v_u_61.Text = p113
        return p112;
    end;
    local v_u_114 = false
    v_u_54.set_refresh_on_refocus = function(p115, p116) --[[ Name: set_refresh_on_refocus ]] --[[ Line: 407 ]]
        --[[ Upvalues: (ref 1): v_u_114 ]]
        v_u_114 = p116
        return p115;
    end;
    local v_u_117 = v_u_2:new()
    v_u_54.add_fn_behaviour_update = function(p118, p119) --[[ Name: add_fn_behaviour_update ]] --[[ Line: 413 ]]
        --[[ Upvalues: (copy 1): v_u_117 ]]
        v_u_117:push_back(p119)
        return p118;
    end;
    local v_u_120 = v_u_2:new()
    v_u_54.add_fn_element_behaviour_update = function(p121, p122) --[[ Name: add_fn_element_behaviour_update ]] --[[ Line: 419 ]]
        --[[ Upvalues: (copy 1): v_u_120 ]]
        v_u_120:push_back(p122)
        return p121;
    end;
    local v_u_123 = false
    v_u_54.set_do_not_update_while_camera_transitioning = function(p124, p125) --[[ Name: set_do_not_update_while_camera_transitioning ]] --[[ Line: 425 ]]
        --[[ Upvalues: (ref 1): v_u_123 ]]
        v_u_123 = p125
        return p124;
    end;
    v_u_54.visual_update = function(p126, p127, p128) --[[ Name: visual_update ]] --[[ Line: 430 ]]
        --[[ Upvalues: (ref 1): v_u_123, (ref 2): v_u_1, (copy 3): p_u_44 ]]
        if v_u_123 == true then
            local v_u_129 = false
            v_u_1:ptry(function() --[[ Line: 433 ]]
                --[[ Upvalues: (ref 1): p_u_44, (ref 2): v_u_129 ]]
                local v130 = p_u_44._lobby_join:get_lobby()
                if v130 and v130:transition_local_camera_cframe_finished() == false then
                    v_u_129 = true
                end;
            end)
            if v_u_129 == true then
                return;
            end;
        end;
        p126:visual_update_base(p127, p128)
    end;
    v_u_54.behaviour_update = function(p131, p132, p133) --[[ Name: behaviour_update ]] --[[ Line: 448 ]]
        --[[ Upvalues: (copy 1): p_u_44, (ref 2): v_u_123, (ref 3): v_u_10, (copy 4): v_u_117, (copy 5): v_u_120, (copy 6): v_u_75 ]]
        p131:behaviour_update_base(p132, p_u_44)
        if v_u_123 ~= true or p131._current_mode == v_u_10.MODE_OPEN then
            for _, v134 in v_u_117:key_itr() do
                v134(p132, p133, p131)
            end;
            if v_u_120:count() > 0 then
                for _, v135 in v_u_75:get_display_elements():key_itr() do
                    for _, v136 in v_u_120:key_itr() do
                        v136(v135, p132, p133, p131)
                    end;
                end;
            end;
        end;
    end;
    v_u_54.on_refocus = function(p137) --[[ Name: on_refocus ]] --[[ Line: 468 ]]
        --[[ Upvalues: (ref 1): v_u_114 ]]
        if v_u_114 == true then
            p137:refresh()
        else
            p137:page_update()
        end;
    end;
    local v_u_138 = nil
    v_u_54.set_fn_on_remove = function(p139, p140) --[[ Name: set_fn_on_remove ]] --[[ Line: 477 ]]
        --[[ Upvalues: (ref 1): v_u_138 ]]
        v_u_138 = p140
        return p139;
    end;
    v_u_54.do_remove = function(p141, _) --[[ Name: do_remove ]] --[[ Line: 482 ]]
        --[[ Upvalues: (ref 1): v_u_138, (ref 2): p_u_51 ]]
        if v_u_138 then
            v_u_138(p141)
        end;
        p_u_51:Destroy()
    end;
    local v_u_142 = v_u_2:new()
    v_u_54.add_fn_on_layout = function(p143, p144) --[[ Name: add_fn_on_layout ]] --[[ Line: 490 ]]
        --[[ Upvalues: (copy 1): v_u_142 ]]
        v_u_142:push_back(p144)
        return p143;
    end;
    local v_u_145 = Vector2.new(0.8, 0.8)
    v_u_54.set_rescale_nxy = function(p146, p147) --[[ Name: set_rescale_nxy ]] --[[ Line: 496 ]]
        --[[ Upvalues: (ref 1): v_u_145 ]]
        v_u_145 = p147
        return p146;
    end;
    local v_u_148 = Vector2.new(0.5, 0.5)
    v_u_54.set_position_nxy = function(p149, p150) --[[ Name: set_position_nxy ]] --[[ Line: 502 ]]
        --[[ Upvalues: (ref 1): v_u_148 ]]
        v_u_148 = p150
        return p149;
    end;
    local v_u_151 = 1
    local v_u_152 = 1
    v_u_54.layout = function(p153) --[[ Name: layout ]] --[[ Line: 509 ]]
        --[[ Upvalues: (copy 1): p_u_45, (ref 2): v_u_145, (ref 3): v_u_152, (ref 4): v_u_148, (ref 5): p_u_51, (copy 6): v_u_75, (copy 7): v_u_142 ]]
        p153:opt_rescale_to_max_nxy(p_u_45, v_u_145.X, v_u_145.Y, v_u_152)
        local v154, v155 = p153:opt_update_cframe_params(p_u_45, {
            ["PositionNXY"] = v_u_148,
            ["OffsetXYZ"] = p153:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v154 == true then
            p_u_51:SetPrimaryPartCFrame(v155)
        end;
        v_u_75:layout()
        if v_u_142:count() > 0 then
            for _, v156 in v_u_142:key_itr() do
                v156(p153)
            end;
        end;
    end;
    local v_u_157 = false
    v_u_54.use_r_set_alpha_v2 = function(p158, p159) --[[ Name: use_r_set_alpha_v2 ]] --[[ Line: 529 ]]
        --[[ Upvalues: (ref 1): v_u_157 ]]
        v_u_157 = p159
        return p158;
    end;
    v_u_54.set_alpha = function(_, p160) --[[ Name: set_alpha ]] --[[ Line: 535 ]]
        --[[ Upvalues: (ref 1): v_u_151, (ref 2): v_u_157, (ref 3): v_u_1, (ref 4): p_u_51 ]]
        if v_u_151 ~= p160 then
            v_u_151 = p160
            if v_u_157 then
                v_u_1:r_set_alpha(p_u_51, v_u_151, nil, v_u_1:r_set_alpha_v2compat_params())
                return;
            end;
            v_u_1:r_set_alpha(p_u_51, v_u_151)
        end;
    end;
    v_u_54.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 545 ]]
        --[[ Upvalues: (ref 1): v_u_151 ]]
        return v_u_151;
    end;
    v_u_54.set_scale = function(_, p161) --[[ Name: set_scale ]] --[[ Line: 546 ]]
        --[[ Upvalues: (ref 1): v_u_152 ]]
        v_u_152 = p161
    end;
    v_u_54.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 547 ]]
        --[[ Upvalues: (ref 1): v_u_152 ]]
        return v_u_152;
    end;
    v_u_54.get_native_size = function(p162) --[[ Name: get_native_size ]] --[[ Line: 549 ]]
        return p162._native_size;
    end;
    v_u_54.get_size = function(p163) --[[ Name: get_size ]] --[[ Line: 552 ]]
        return p163._size;
    end;
    v_u_54.set_size = function(p164, p165) --[[ Name: set_size ]] --[[ Line: 555 ]]
        --[[ Upvalues: (ref 1): p_u_51 ]]
        p164._size = p165
        p_u_51.PrimaryPart.Size = Vector3.new(p165.X, p165.Y, 0)
    end;
    v_u_54.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 559 ]]
        --[[ Upvalues: (ref 1): p_u_51 ]]
        return p_u_51.PrimaryPart.Position;
    end;
    v_u_54.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 562 ]]
        --[[ Upvalues: (ref 1): p_u_51 ]]
        return p_u_51.PrimaryPart.SurfaceGui;
    end;
    v_u_54.set_showing = function(_, p166) --[[ Name: set_showing ]] --[[ Line: 565 ]]
        --[[ Upvalues: (ref 1): p_u_51, (ref 2): v_u_8 ]]
        if p166 then
            p_u_51.Parent = v_u_8:get_world_ui_folder()
        else
            p_u_51.Parent = nil
        end;
    end;
    v_u_54.get_uichild_parent = function(_) --[[ Name: get_uichild_parent ]] --[[ Line: 572 ]]
        --[[ Upvalues: (ref 1): p_u_51 ]]
        return p_u_51.PrimaryPart;
    end;
    v_u_54.get_obj = function(_) --[[ Name: get_obj ]] --[[ Line: 573 ]]
        --[[ Upvalues: (ref 1): p_u_51 ]]
        return p_u_51;
    end;
    f_cons()
    return v_u_54;
end;
return v_u_15;
