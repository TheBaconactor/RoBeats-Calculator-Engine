-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:46 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_7 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_8 = require(game.ReplicatedStorage.Shared.ListAdapter)
local v_u_9 = {
    ["ListElement"] = {}
}
v_u_9.ListElement.new = function(_, p_u_10, p_u_11, p_u_12) --[[ Name: new ]] --[[ Line: 17 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_5, (copy 3): v_u_6, (copy 4): v_u_1 ]]
    local v13 = {}
    local v_u_14 = nil
    local v_u_15 = nil
    local v_u_16 = nil
    local v_u_17 = nil
    local v_u_18 = nil
    v13.cons = function(_) --[[ Name: cons ]] --[[ Line: 28 ]]
        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_4, (copy 3): p_u_11, (copy 4): p_u_12, (ref 5): v_u_15, (copy 6): p_u_10, (ref 7): v_u_5, (ref 8): v_u_6, (ref 9): v_u_18, (ref 10): v_u_16, (ref 11): v_u_17 ]]
        v_u_14 = v_u_4:new(p_u_11, p_u_11:get_uichild_parent(), p_u_12.MainSurface):set_default_sgui()
        v_u_15 = p_u_11:add_cycle_element(p_u_10, 1, v_u_5:new(v_u_4:new(v_u_14, p_u_12.MainSurface, p_u_12.SelectButton), p_u_10._spui, function() --[[ Line: 33 ]]
            --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_6, (ref 3): v_u_18, (ref 4): p_u_11 ]]
            p_u_10._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            if v_u_18 ~= nil then
                p_u_11:on_player_selected(v_u_18)
            end;
        end))
        local l_Frame_0 = p_u_12.MainSurface.SurfaceGui.Frame
        v_u_16 = l_Frame_0.NameDisplay
        v_u_17 = l_Frame_0.PlayerIcon
    end;
    v13.set_display_element = function(_, p19) --[[ Name: set_display_element ]] --[[ Line: 47 ]]
        --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_16, (ref 3): v_u_17, (ref 4): v_u_1, (ref 5): v_u_15 ]]
        v_u_18 = p19
        if v_u_18 then
            v_u_16.Text = v_u_18.Name
            v_u_17.Image = v_u_1:transparent_assetid()
            v_u_1:get_user_thumbnail(v_u_18.UserId, function(p20, _) --[[ Line: 52 ]]
                --[[ Upvalues: (ref 1): v_u_17 ]]
                v_u_17.Image = p20
            end, false)
        else
            v_u_15:set_visible(false)
        end;
    end;
    v13.set_visible = function(_, p21) --[[ Name: set_visible ]] --[[ Line: 60 ]]
        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_15 ]]
        v_u_14:set_visible(p21)
        v_u_15:set_visible(p21)
    end;
    v13.layout = function(_) --[[ Name: layout ]] --[[ Line: 65 ]]
        --[[ Upvalues: (ref 1): v_u_14 ]]
        v_u_14:layout()
    end;
    v13:cons()
    return v13;
end;
v_u_9.new = function(_, p_u_22, p_u_23, p_u_24, p_u_25, p_u_26) --[[ Name: new ]] --[[ Line: 73 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_1, (copy 4): v_u_8, (copy 5): v_u_5, (copy 6): v_u_4, (copy 7): v_u_6, (copy 8): v_u_9, (copy 9): v_u_7 ]]
    local v27 = v_u_3:new(p_u_23, p_u_24)
    local v_u_28 = nil
    local v_u_29 = nil
    local v_u_30 = nil
    local v_u_31 = nil
    local v_u_32 = v_u_2:new()
    v27.get_players_list = function(_) --[[ Name: get_players_list ]] --[[ Line: 83 ]]
        --[[ Upvalues: (copy 1): v_u_32 ]]
        return v_u_32;
    end;
    v27.fill_players_list = function(_, p33) --[[ Name: fill_players_list ]] --[[ Line: 84 ]]
        --[[ Upvalues: (copy 1): v_u_32, (ref 2): v_u_1 ]]
        v_u_32:clear()
        for _, v34 in pairs(v_u_1:get_players():GetPlayers()) do
            if v34.UserId == v_u_1:get_local_userid() then
                if p33 then
                    v_u_32:push_back(v34)
                end;
            else
                v_u_32:push_back(v34)
            end;
        end;
        v_u_32:sort(function(p35, p36) --[[ Line: 95 ]]
            return string.lower(p35.Name) < string.lower(p36.Name);
        end)
    end;
    local v_u_43 = v_u_8:new():set_fn_get_data_list(function() --[[ Line: 99 ]]
        --[[ Upvalues: (copy 1): v_u_32 ]]
        return v_u_32;
    end):set_fn_set_element_data(function(p37, p38) --[[ Line: 100 ]]
        if p38 == nil then
            p37:set_visible(false)
        else
            p37:set_visible(true)
            p37:set_display_element(p38)
        end;
    end):set_fn_next_prev_visible(function(p39, p40) --[[ Line: 108 ]]
        --[[ Upvalues: (ref 1): v_u_30, (ref 2): v_u_31 ]]
        v_u_30:set_visible(p39)
        v_u_31:set_visible(p40)
    end):set_fn_update_page_display(function(p41, p42) --[[ Line: 112 ]]
        --[[ Upvalues: (ref 1): v_u_29 ]]
        v_u_29.Text = string.format("%d/%d", p41, p42)
    end)
    v27.cons = function(p_u_44) --[[ Name: cons ]] --[[ Line: 116 ]]
        --[[ Upvalues: (ref 1): v_u_28, (ref 2): v_u_1, (ref 3): v_u_29, (copy 4): v_u_43, (ref 5): v_u_30, (copy 6): p_u_22, (ref 7): v_u_5, (ref 8): v_u_4, (copy 9): p_u_23, (ref 10): v_u_6, (ref 11): v_u_31, (copy 12): p_u_24, (copy 13): p_u_26, (ref 14): v_u_9, (copy 15): p_u_25 ]]
        v_u_28 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.PlayerSelectUI:Clone()
        v_u_28.Name = v_u_1:gen_name(v_u_28.Name)
        p_u_44:set_showing(true)
        p_u_44._native_size = v_u_28.PrimaryPart.Size
        p_u_44._size = p_u_44._native_size
        local l_Frame_1 = v_u_28.MainSurface.SurfaceGui.Frame
        v_u_29 = l_Frame_1.PageDisplay
        local l_EmptyDisplay_0 = l_Frame_1.EmptyDisplay
        v_u_43:set_fn_is_empty(function(p45) --[[ Line: 128 ]]
            --[[ Upvalues: (copy 1): l_EmptyDisplay_0 ]]
            l_EmptyDisplay_0.Visible = p45
        end)
        v_u_30 = p_u_44:add_cycle_element(p_u_22, 1, v_u_5:new(v_u_4:new(p_u_44, v_u_28.PrimaryPart, v_u_28.ListButtonDown), p_u_23, function() --[[ Line: 135 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_6, (ref 3): v_u_43 ]]
            p_u_22._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            v_u_43:next_page()
        end))
        v_u_31 = p_u_44:add_cycle_element(p_u_22, 1, v_u_5:new(v_u_4:new(p_u_44, v_u_28.PrimaryPart, v_u_28.ListButtonUp), p_u_23, function() --[[ Line: 144 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_6, (ref 3): v_u_43 ]]
            p_u_22._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            v_u_43:prev_page()
        end))
        p_u_44:add_cycle_element(p_u_22, 1, v_u_5:new(v_u_4:new(p_u_44, v_u_28.PrimaryPart, v_u_28.BackButtonSurface), p_u_23, function() --[[ Line: 153 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_6, (ref 3): p_u_24, (copy 4): p_u_44, (ref 5): p_u_26 ]]
            p_u_22._sfx_manager:play_sfx(v_u_6.SFX_MENU_CLOSE)
            p_u_24:remove_menu(p_u_44)
            p_u_26(nil)
        end))
        local l_Anchors_0 = v_u_28.Anchors
        v_u_43:create_list_elements_from_anchors_and_proto({
            l_Anchors_0.Anchor1,
            l_Anchors_0.Anchor2,
            l_Anchors_0.Anchor3,
            l_Anchors_0.Anchor4,
            l_Anchors_0.Anchor5,
            l_Anchors_0.Anchor6,
            l_Anchors_0.Anchor7
        }, v_u_28.ListElement, v_u_28, function(p46) --[[ Line: 173 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): p_u_22, (copy 3): p_u_44 ]]
            return v_u_9.ListElement:new(p_u_22, p_u_44, p46);
        end)
        p_u_25(p_u_44)
        v_u_43:page_update()
        p_u_44:transition_update_visual(0)
        p_u_44:layout()
    end;
    v27.on_player_selected = function(p47, p48) --[[ Name: on_player_selected ]] --[[ Line: 185 ]]
        --[[ Upvalues: (copy 1): p_u_26, (copy 2): p_u_24 ]]
        p_u_26(p48)
        p_u_24:remove_menu(p47)
    end;
    v27.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 190 ]]
        --[[ Upvalues: (ref 1): v_u_28 ]]
        v_u_28:Destroy()
    end;
    local v_u_49 = 1
    local v_u_50 = 1
    v27.layout = function(p51) --[[ Name: layout ]] --[[ Line: 196 ]]
        --[[ Upvalues: (copy 1): p_u_23, (ref 2): v_u_50, (ref 3): v_u_28, (copy 4): v_u_43 ]]
        p51:opt_rescale_to_max_nxy(p_u_23, 0.8, 0.8, v_u_50)
        local v52, v53 = p51:opt_update_cframe_params(p_u_23, {
            ["PositionNXY"] = Vector2.new(0.5, 0.5),
            ["OffsetXYZ"] = p51:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v52 == true then
            v_u_28:SetPrimaryPartCFrame(v53)
        end;
        v_u_43:layout()
    end;
    v27.set_alpha = function(_, p54) --[[ Name: set_alpha ]] --[[ Line: 210 ]]
        --[[ Upvalues: (ref 1): v_u_49, (ref 2): v_u_1, (ref 3): v_u_28 ]]
        if v_u_49 ~= p54 then
            v_u_49 = p54
            v_u_1:r_set_alpha(v_u_28, v_u_49)
        end;
    end;
    v27.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 216 ]]
        --[[ Upvalues: (ref 1): v_u_49 ]]
        return v_u_49;
    end;
    v27.set_scale = function(_, p55) --[[ Name: set_scale ]] --[[ Line: 217 ]]
        --[[ Upvalues: (ref 1): v_u_50 ]]
        v_u_50 = p55
    end;
    v27.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 218 ]]
        --[[ Upvalues: (ref 1): v_u_50 ]]
        return v_u_50;
    end;
    v27.get_native_size = function(p56) --[[ Name: get_native_size ]] --[[ Line: 220 ]]
        return p56._native_size;
    end;
    v27.get_size = function(p57) --[[ Name: get_size ]] --[[ Line: 223 ]]
        return p57._size;
    end;
    v27.set_size = function(p58, p59) --[[ Name: set_size ]] --[[ Line: 226 ]]
        --[[ Upvalues: (ref 1): v_u_28 ]]
        p58._size = p59
        v_u_28.PrimaryPart.Size = Vector3.new(p59.X, p59.Y, 0)
    end;
    v27.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 230 ]]
        --[[ Upvalues: (ref 1): v_u_28 ]]
        return v_u_28.PrimaryPart.Position;
    end;
    v27.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 233 ]]
        --[[ Upvalues: (ref 1): v_u_28 ]]
        return v_u_28.PrimaryPart.SurfaceGui;
    end;
    v27.set_showing = function(_, p60) --[[ Name: set_showing ]] --[[ Line: 236 ]]
        --[[ Upvalues: (ref 1): v_u_28, (ref 2): v_u_7 ]]
        if p60 then
            v_u_28.Parent = v_u_7:get_world_ui_folder()
        else
            v_u_28.Parent = nil
        end;
    end;
    v27.get_uichild_parent = function(_) --[[ Name: get_uichild_parent ]] --[[ Line: 243 ]]
        --[[ Upvalues: (ref 1): v_u_28 ]]
        return v_u_28.PrimaryPart;
    end;
    v27:cons()
    return v27;
end;
return v_u_9;
