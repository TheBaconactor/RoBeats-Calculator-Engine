-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:44 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_4 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_6 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_8 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_9 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_10 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_11 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_12 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_13 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_14 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_15 = require(game.ReplicatedStorage.Lobby.Menus.TradesUI)
local v_u_16 = require(game.ReplicatedStorage.Lobby.UI.MarketplaceUI.MarketplaceTab)
local v_u_17 = require(game.ReplicatedStorage.Lobby.UI.MarketplaceUI.MarketplaceTab_Market)
local v_u_18 = require(game.ReplicatedStorage.Lobby.UI.MarketplaceUI.MarketplaceTab_MySales)
local v_u_19 = require(game.ReplicatedStorage.Lobby.Dialogue.MarketplaceDialogue)
local v_u_20 = require(game.ReplicatedStorage.PlayerInfo.MarketplaceUtils)
local v_u_21 = {
    ["Mode"] = {
        ["Loading"] = 0,
        ["Ready"] = 1,
        ["Kill"] = -1
    }
}
local l_Market_0 = v_u_16.Tab.Market
v_u_21.new = function(_, p_u_22, p_u_23, p_u_24) --[[ Name: new ]] --[[ Line: 36 ]]
    --[[ Upvalues: (copy 1): v_u_4, (ref 2): l_Market_0, (copy 3): v_u_21, (copy 4): v_u_2, (copy 5): v_u_3, (copy 6): v_u_1, (copy 7): v_u_11, (copy 8): v_u_12, (copy 9): v_u_6, (copy 10): v_u_5, (copy 11): v_u_8, (copy 12): v_u_17, (copy 13): v_u_18, (copy 14): v_u_16, (copy 15): v_u_15, (copy 16): v_u_19, (copy 17): v_u_20, (copy 18): v_u_9, (copy 19): v_u_10, (copy 20): v_u_14, (copy 21): v_u_7, (copy 22): v_u_13 ]]
    local v_u_25 = v_u_4:new(p_u_23, p_u_24)
    local v_u_26 = nil
    local v_u_27 = nil
    v_u_25.get_selected_tab = function(_) --[[ Name: get_selected_tab ]] --[[ Line: 41 ]]
        --[[ Upvalues: (ref 1): l_Market_0 ]]
        return l_Market_0;
    end;
    local l_Loading_0 = v_u_21.Mode.Loading
    v_u_25.get_current_mode = function(_) --[[ Name: get_current_mode ]] --[[ Line: 44 ]]
        --[[ Upvalues: (ref 1): l_Loading_0 ]]
        return l_Loading_0;
    end;
    local v_u_28 = v_u_2:new()
    local v_u_29 = v_u_3:new()
    local v_u_30 = nil
    local v_u_31 = nil
    local v_u_32 = nil
    local v_u_33 = nil
    local v_u_34 = nil
    local v_u_35 = nil
    v_u_25.get_empty_display = function(_) --[[ Name: get_empty_display ]] --[[ Line: 56 ]]
        --[[ Upvalues: (ref 1): v_u_35 ]]
        return v_u_35;
    end;
    local v_u_36 = nil
    local v_u_37 = v_u_3:new()
    v_u_25.get_sort_section_and_buttons = function(_) --[[ Name: get_sort_section_and_buttons ]] --[[ Line: 60 ]]
        --[[ Upvalues: (ref 1): v_u_36, (copy 2): v_u_37 ]]
        return v_u_36, v_u_37;
    end;
    local function f_cons() --[[ Name: cons ]] --[[ Line: 62 ]]
        --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_1, (ref 3): v_u_11, (ref 4): v_u_27, (ref 5): v_u_12, (copy 6): p_u_22, (ref 7): v_u_33, (ref 8): v_u_34, (ref 9): v_u_35, (copy 10): v_u_25, (copy 11): v_u_29, (ref 12): v_u_6, (ref 13): v_u_5, (copy 14): p_u_23, (ref 15): v_u_8, (ref 16): l_Loading_0, (ref 17): v_u_21, (copy 18): p_u_24, (ref 19): v_u_36, (ref 20): v_u_3, (copy 21): v_u_28, (ref 22): l_Market_0, (copy 23): v_u_37, (ref 24): v_u_17, (ref 25): v_u_18, (ref 26): v_u_30, (ref 27): v_u_16, (ref 28): v_u_31, (ref 29): v_u_15, (ref 30): v_u_32, (ref 31): v_u_19, (ref 32): v_u_20, (ref 33): v_u_9, (ref 34): v_u_10, (ref 35): v_u_14 ]]
        v_u_26 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.MarketplaceUI:Clone()
        v_u_26.Name = v_u_1:gen_name(v_u_26.Name)
        v_u_26.Parent = v_u_11:get_world_ui_folder()
        v_u_27 = v_u_26.MainSurface.SurfaceGui.Frame
        v_u_12:is_non_nil(v_u_27)
        p_u_22:set_character_random_position_around_anchors_fn(function() --[[ Line: 69 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            return v_u_11:get_lobby_anchors().Marketplace.StandAnchor, v_u_11:get_lobby_anchors().Marketplace.LookAnchor;
        end)
        p_u_22:transition_local_camera_to_anchors_fn(function() --[[ Line: 73 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            return v_u_11:get_lobby_anchors().Marketplace.CameraAnchor, v_u_11:get_lobby_anchors().Marketplace.LookAnchor;
        end)
        v_u_33 = v_u_27.LoadedFrame.CoinSection.Display
        v_u_34 = v_u_27.LoadedFrame.StarSection.Display
        v_u_35 = v_u_27.LoadedFrame.EmptyDisplay
        v_u_33.Text = ""
        v_u_34.Text = ""
        v_u_25._native_size = v_u_26.PrimaryPart.Size
        v_u_25._size = v_u_25._native_size
        v_u_29:push_back(v_u_25:add_cycle_element(p_u_22, 1, v_u_6:new(v_u_5:new(v_u_25, v_u_26.PrimaryPart, v_u_26.BackButtonSurface), p_u_23, function() --[[ Line: 90 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_8, (ref 3): l_Loading_0, (ref 4): v_u_21, (ref 5): p_u_24, (ref 6): v_u_25 ]]
            p_u_22._sfx_manager:play_sfx(v_u_8.SFX_MENU_CLOSE)
            l_Loading_0 = v_u_21.Mode.Kill
            p_u_24:remove_menu(v_u_25)
        end)))
        v_u_36 = v_u_27.LoadedFrame.SortSection
        for v_u_38, v39 in v_u_3:new({
            v_u_26.SortItems.Button1,
            v_u_26.SortItems.Button2,
            v_u_26.SortItems.Button3,
            v_u_26.SortItems.Button4
        }):key_itr() do
            local v40 = v_u_6:new(v_u_5:new(v_u_25, v_u_26.PrimaryPart, v39), p_u_23, function() --[[ Line: 102 ]]
                --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_8, (ref 3): v_u_28, (ref 4): l_Market_0, (copy 5): v_u_38 ]]
                p_u_22._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
                if v_u_28:get(l_Market_0) ~= nil then
                    v_u_28:get(l_Market_0):on_sort_button_index_pressed(v_u_38)
                end;
            end):set_auto_zoffset_behaviour(true)
            v40:bind_data(v_u_6:button_bind_anim_toggle(v40, function() --[[ Line: 111 ]]
                --[[ Upvalues: (ref 1): v_u_25 ]]
                return v_u_25:get_alpha();
            end))
            v_u_37:push_back(v_u_25:add_cycle_element(p_u_22, 1, v40))
        end;
        local v41 = v_u_17:new(p_u_22, p_u_23, p_u_24, v_u_25, v_u_26)
        v_u_28:add(v41:get_tab(), v41)
        local v42 = v_u_18:new(p_u_22, p_u_23, p_u_24, v_u_25, v_u_26)
        v_u_28:add(v42:get_tab(), v42)
        v_u_30 = v_u_25:add_cycle_element(p_u_22, 1, v_u_6:new(v_u_5:new(v_u_25, v_u_26.PrimaryPart, v_u_26.MarketplaceButton), p_u_23, function() --[[ Line: 128 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_8, (ref 3): l_Market_0, (ref 4): v_u_16, (ref 5): v_u_25 ]]
            p_u_22._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            l_Market_0 = v_u_16.Tab.Market
            v_u_25:update_mode()
        end))
        v_u_29:push_back(v_u_30)
        v_u_31 = v_u_25:add_cycle_element(p_u_22, 1, v_u_6:new(v_u_5:new(v_u_25, v_u_26.PrimaryPart, v_u_26.MySalesButton), p_u_23, function() --[[ Line: 139 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_8, (ref 3): l_Market_0, (ref 4): v_u_16, (ref 5): v_u_25 ]]
            p_u_22._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            l_Market_0 = v_u_16.Tab.MySales
            v_u_25:update_mode()
        end))
        v_u_29:push_back(v_u_31)
        v_u_29:push_back(v_u_25:add_cycle_element(p_u_22, 1, v_u_6:new(v_u_5:new(v_u_25, v_u_26.PrimaryPart, v_u_26.TradesButton), p_u_23, function() --[[ Line: 150 ]]
            --[[ Upvalues: (ref 1): p_u_24, (ref 2): v_u_15, (ref 3): p_u_22, (ref 4): p_u_23, (ref 5): v_u_25, (ref 6): v_u_8 ]]
            p_u_24:push_menu(v_u_15:new(p_u_22, p_u_23, p_u_24))
            p_u_24:remove_menu(v_u_25)
            p_u_22._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
        end)))
        v_u_32 = v_u_19:new(p_u_22, v_u_25, v_u_25, v_u_26)
        v_u_25:update_mode()
        v_u_25:transition_update_visual(0)
        v_u_25:set_alpha(0)
        v_u_25:layout()
        local function _() --[[ Name: on_loaded ]] --[[ Line: 165 ]]
            --[[ Upvalues: (ref 1): l_Loading_0, (ref 2): v_u_21, (ref 3): v_u_25 ]]
            l_Loading_0 = v_u_21.Mode.Loaded
            v_u_25:update_mode()
        end;
        p_u_22._player_blob_manager:do_sync(function(p43) --[[ Line: 170 ]]
            --[[ Upvalues: (ref 1): v_u_20, (ref 2): p_u_22, (ref 3): v_u_9, (ref 4): v_u_8, (ref 5): p_u_24, (ref 6): v_u_10, (ref 7): p_u_23, (ref 8): v_u_14, (ref 9): l_Loading_0, (ref 10): v_u_21, (ref 11): v_u_25 ]]
            if v_u_20:playerblob_has_any_purchased_sales(p43) then
                p_u_22._evt:wait_on_event_once(v_u_9.EVT_Marketplace_ServerClaimSoldSalesResponse, function(p44) --[[ Line: 172 ]]
                    --[[ Upvalues: (ref 1): v_u_20, (ref 2): p_u_22, (ref 3): v_u_8, (ref 4): p_u_24, (ref 5): v_u_10, (ref 6): p_u_23, (ref 7): v_u_14, (ref 8): l_Loading_0, (ref 9): v_u_21, (ref 10): v_u_25 ]]
                    local v_u_45 = v_u_20:sales_table_to_list(p44)
                    p_u_22._player_blob_manager:do_sync(function() --[[ Line: 174 ]]
                        --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_8, (copy 3): v_u_45, (ref 4): p_u_24, (ref 5): v_u_10, (ref 6): p_u_23, (ref 7): v_u_14, (ref 8): l_Loading_0, (ref 9): v_u_21, (ref 10): v_u_25 ]]
                        p_u_22._sfx_manager:play_sfx(v_u_8.SFX_FANFARE)
                        for v46 = 1, v_u_45:count() do
                            local v47 = v_u_45:get(v46)
                            p_u_24:push_menu(v_u_10:new(p_u_22, p_u_23, p_u_24):set_text("Sold!", string.format("Sold %d %s(s) to %s for %d coins.", v47:get_count(), v_u_14:singleton():get_material_name(v47:get_materialid()), v47:get_purchased_by(), v47:get_price())))
                        end;
                        l_Loading_0 = v_u_21.Mode.Loaded
                        v_u_25:update_mode()
                    end)
                end)
                p_u_22._evt:fire_event_to_server(v_u_9.EVT_Marketplace_ClientClaimSoldSales)
            else
                l_Loading_0 = v_u_21.Mode.Loaded
                v_u_25:update_mode()
            end;
        end)
    end;
    v_u_25.update_mode = function(p48) --[[ Name: update_mode ]] --[[ Line: 196 ]]
        --[[ Upvalues: (ref 1): l_Loading_0, (ref 2): v_u_21, (ref 3): v_u_27, (copy 4): v_u_28, (copy 5): v_u_29, (copy 6): v_u_37, (ref 7): v_u_36, (ref 8): v_u_35, (ref 9): l_Market_0, (ref 10): v_u_1, (ref 11): v_u_30, (ref 12): v_u_31, (ref 13): v_u_16 ]]
        if l_Loading_0 == v_u_21.Mode.Loading then
            v_u_27.LoadedFrame.Visible = false
            v_u_27.LoadingFrame.Visible = true
            for _, v49 in v_u_28:key_itr() do
                v49:set_visible(false)
            end;
            for v50 = 1, v_u_29:count() do
                v_u_29:get(v50):set_visible(false)
            end;
            for v51 = 1, v_u_37:count() do
                v_u_37:get(v51):set_visible(false)
            end;
            v_u_36.Visible = false
            v_u_35.Visible = false
        elseif l_Loading_0 == v_u_21.Mode.Loaded then
            v_u_27.LoadedFrame.Visible = true
            v_u_27.LoadingFrame.Visible = false
            v_u_35.Visible = false
            for v52, v53 in v_u_28:key_itr() do
                v53:set_visible(v52 == l_Market_0)
            end;
            for v54 = 1, v_u_29:count() do
                v_u_29:get(v54):set_visible(true)
            end;
            local v55 = v_u_1:get_list_of_children_of_classname(v_u_30:get_part(), "ImageLabel")
            local v56 = v_u_1:get_list_of_children_of_classname(v_u_31:get_part(), "ImageLabel")
            if l_Market_0 == v_u_16.Tab.Market then
                v_u_1:list_set_alpha_name(v55, {
                    ["ImageAlpha"] = 1
                })
                v_u_1:list_set_alpha_name(v56, {
                    ["ImageAlpha"] = 0.4
                })
            else
                v_u_1:list_set_alpha_name(v55, {
                    ["ImageAlpha"] = 0.4
                })
                v_u_1:list_set_alpha_name(v56, {
                    ["ImageAlpha"] = 1
                })
            end;
            v_u_1:r_set_alpha(v_u_30:get_part(), p48:get_alpha())
            v_u_1:r_set_alpha(v_u_31:get_part(), p48:get_alpha())
            for v57 = 1, v_u_37:count() do
                v_u_37:get(v57):set_visible(false)
            end;
            v_u_36.Visible = false
            if v_u_28:get(l_Market_0) ~= nil then
                v_u_28:get(l_Market_0):sort_buttons_update_mode()
            end;
        end;
    end;
    v_u_25.layout = function(p58) --[[ Name: layout ]] --[[ Line: 246 ]]
        --[[ Upvalues: (copy 1): p_u_23, (ref 2): v_u_26, (ref 3): v_u_32, (copy 4): v_u_28 ]]
        p_u_23:uiobj_rescale_to_max_nxy(p58, 0.75, 0.85, p58:get_scale())
        v_u_26:SetPrimaryPartCFrame(p_u_23:get_cframe({
            ["PositionNXY"] = Vector2.new(0.55, 0.5),
            ["OffsetXYZ"] = p58:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        }))
        v_u_32:layout()
        for _, v59 in v_u_28:key_itr() do
            v59:layout()
        end;
    end;
    v_u_25.behaviour_update = function(p60, p61, p62) --[[ Name: behaviour_update ]] --[[ Line: 260 ]]
        --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_32, (copy 3): v_u_28, (ref 4): l_Market_0 ]]
        p60:behaviour_update_base(p61, p62)
        p60:update_blob_sync()
        if p60._current_mode == v_u_7.MODE_OPEN then
            v_u_32:update(p61)
        end;
        v_u_28:get(l_Market_0):behaviour_update(p61)
    end;
    local v_u_63 = -1
    v_u_25.update_blob_sync = function(_) --[[ Name: update_blob_sync ]] --[[ Line: 270 ]]
        --[[ Upvalues: (copy 1): p_u_22, (ref 2): v_u_63, (ref 3): v_u_33, (ref 4): v_u_1, (ref 5): v_u_13, (ref 6): v_u_34 ]]
        if p_u_22._player_blob_manager:is_synced() and p_u_22._player_blob_manager:get_synced_time() ~= v_u_63 then
            v_u_63 = p_u_22._player_blob_manager:get_synced_time()
            local v64 = p_u_22._player_blob_manager:get_player_blob()
            v_u_33.Text = v_u_1:comma_value(v_u_13:get_coin_currency(v64))
            v_u_34.Text = v_u_1:comma_value(v_u_13:get_star_currency(v64))
        end;
    end;
    v_u_25.visual_update = function(p65, p66, p67) --[[ Name: visual_update ]] --[[ Line: 280 ]]
        --[[ Upvalues: (copy 1): p_u_22 ]]
        if p_u_22:transition_local_camera_cframe_finished() ~= false then
            p65:visual_update_base(p66, p67)
        end;
    end;
    v_u_25.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 287 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        v_u_26:Destroy()
    end;
    local v_u_68 = -1
    v_u_25.set_alpha = function(_, p69, p70) --[[ Name: set_alpha ]] --[[ Line: 292 ]]
        --[[ Upvalues: (ref 1): v_u_68, (ref 2): v_u_1, (ref 3): v_u_26 ]]
        if v_u_68 ~= p69 or p70 == true then
            v_u_68 = p69
            v_u_1:r_set_alpha(v_u_26, v_u_68)
        end;
    end;
    v_u_25.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 299 ]]
        --[[ Upvalues: (ref 1): v_u_68 ]]
        return v_u_68;
    end;
    local v_u_71 = 1
    v_u_25.set_scale = function(_, p72) --[[ Name: set_scale ]] --[[ Line: 301 ]]
        --[[ Upvalues: (ref 1): v_u_71 ]]
        v_u_71 = p72
    end;
    v_u_25.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 302 ]]
        --[[ Upvalues: (ref 1): v_u_71 ]]
        return v_u_71;
    end;
    v_u_25.get_native_size = function(p73) --[[ Name: get_native_size ]] --[[ Line: 303 ]]
        return p73._native_size;
    end;
    v_u_25.get_size = function(p74) --[[ Name: get_size ]] --[[ Line: 304 ]]
        return p74._size;
    end;
    v_u_25.set_size = function(p75, p76) --[[ Name: set_size ]] --[[ Line: 305 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        p75._size = p76
        v_u_26.PrimaryPart.Size = Vector3.new(p76.X, p76.Y, 0)
    end;
    v_u_25.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 309 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        return v_u_26.PrimaryPart.Position;
    end;
    v_u_25.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 310 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        return v_u_26.PrimaryPart.SurfaceGui;
    end;
    v_u_25.set_showing = function(_, p77) --[[ Name: set_showing ]] --[[ Line: 311 ]]
        --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_11 ]]
        if p77 then
            v_u_26.Parent = v_u_11:get_world_ui_folder()
        else
            v_u_26.Parent = nil
        end;
    end;
    f_cons()
    return v_u_25;
end;
return v_u_21;
