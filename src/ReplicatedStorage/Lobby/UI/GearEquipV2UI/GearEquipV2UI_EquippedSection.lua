-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:54 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_6 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Menu.SPUIButton)
require(game.ReplicatedStorage.Menu.MenuSystem)
require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_8 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_9 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_10 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_11 = require(game.ReplicatedStorage.Lobby.UI.GearEquipV2UI.GearEquipV2GearStatDisplay)
local v12 = {}
local v_u_38 = {
    ["new"] = function(_, p_u_13, p_u_14, p_u_15, p_u_16, p_u_17) --[[ Name: new ]] --[[ Line: 22 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_9, (copy 3): v_u_1, (copy 4): v_u_10 ]]
        local v18 = {}
        local v_u_19 = 1
        v18.set_alpha = function(p20, p21) --[[ Name: set_alpha ]] --[[ Line: 26 ]]
            --[[ Upvalues: (ref 1): v_u_19 ]]
            v_u_19 = p21
            p20:update_alphas()
        end;
        local v_u_22 = nil
        local v_u_23 = v_u_3:new()
        local v_u_24 = v_u_3:new()
        local v_u_25 = 0
        local v_u_26 = v_u_3:new()
        v18.get_uichild = function(_) --[[ Name: get_uichild ]] --[[ Line: 38 ]]
            --[[ Upvalues: (copy 1): p_u_14 ]]
            return p_u_14;
        end;
        v18.add_child_uibutton = function(_, p27) --[[ Name: add_child_uibutton ]] --[[ Line: 39 ]]
            --[[ Upvalues: (copy 1): v_u_26 ]]
            v_u_26:push_back(p27)
        end;
        v18.refresh_from_playerblob = function(p28) --[[ Name: refresh_from_playerblob ]] --[[ Line: 41 ]]
            --[[ Upvalues: (copy 1): p_u_13, (ref 2): v_u_9, (copy 3): p_u_16, (copy 4): p_u_17, (ref 5): v_u_25 ]]
            local v29 = p_u_13._player_blob_manager:get_player_blob()
            local v30 = v_u_9:get_equippedobj_for_slot(v29, p_u_16)
            if v30 == nil then
                p_u_17:set_empty_slot(p_u_16)
                p28:set_buttons_visible(false)
            else
                p_u_17:set_owned_obj(v29, v30.OwnedID)
                if v_u_9:get_visible_for_slot(v29, p_u_16) == true then
                    v_u_25 = 1
                else
                    v_u_25 = 0.2
                end;
                p28:update_alphas()
                p28:set_buttons_visible(true)
            end;
        end;
        v18.toggle_visible = function(_) --[[ Name: toggle_visible ]] --[[ Line: 61 ]]
            --[[ Upvalues: (copy 1): p_u_13, (ref 2): v_u_9, (copy 3): p_u_16, (copy 4): p_u_15 ]]
            local v31 = p_u_13._player_blob_manager:get_player_blob()
            v_u_9:set_visible_for_slot(v31, p_u_16, not v_u_9:get_visible_for_slot(v31, p_u_16))
            p_u_15:gear_updated_local()
            p_u_15:refresh_ui()
        end;
        v18.remove_action = function(_) --[[ Name: remove_action ]] --[[ Line: 68 ]]
            --[[ Upvalues: (copy 1): p_u_13, (ref 2): v_u_9, (copy 3): p_u_16, (copy 4): p_u_15 ]]
            v_u_9:playerblob_unequip_slot(p_u_13._player_blob_manager:get_player_blob(), p_u_16)
            p_u_15:gear_updated_local()
            p_u_15:refresh_ui()
        end;
        v18.layout = function(_) --[[ Name: layout ]] --[[ Line: 75 ]]
            --[[ Upvalues: (copy 1): p_u_14, (copy 2): v_u_26 ]]
            p_u_14:layout()
            for v32 = 1, v_u_26:count() do
                v_u_26:get(v32):layout()
            end;
        end;
        v18.set_visible_button = function(p33, p34) --[[ Name: set_visible_button ]] --[[ Line: 82 ]]
            --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_1, (ref 3): v_u_24, (ref 4): v_u_22 ]]
            v_u_23 = v_u_1:get_list_of_children_of_classname(p34:get_part(), "ImageLabel")
            v_u_24 = v_u_1:get_list_of_children_of_classname(p34:get_part(), "TextLabel")
            v_u_22 = p34
            p33:add_child_uibutton(p34)
            p33:update_alphas()
        end;
        v18.update_alphas = function(_) --[[ Name: update_alphas ]] --[[ Line: 90 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_23, (ref 3): v_u_25, (ref 4): v_u_19, (ref 5): v_u_24, (ref 6): v_u_22 ]]
            v_u_1:list_set_alpha_name(v_u_23, {
                ["ImageAlpha"] = v_u_25 * v_u_19
            })
            v_u_1:list_set_alpha_name(v_u_24, {
                ["TextAlpha"] = v_u_25 * v_u_19
            })
            v_u_1:r_set_alpha(v_u_22:get_part(), v_u_19)
        end;
        v18.set_buttons_visible = function(_, p35) --[[ Name: set_buttons_visible ]] --[[ Line: 96 ]]
            --[[ Upvalues: (copy 1): v_u_26 ]]
            for v36 = 1, v_u_26:count() do
                v_u_26:get(v36):set_visible(p35)
            end;
        end;
        v18.visual_update = function(_, p37, _) --[[ Name: visual_update ]] --[[ Line: 102 ]]
            --[[ Upvalues: (copy 1): p_u_17, (ref 2): v_u_1, (copy 3): p_u_14, (ref 4): v_u_10 ]]
            p_u_17:visual_update(p37)
            if v_u_1:flt_cmp_delta(p_u_14:get_scale(), 1, 0.01) ~= true then
                p_u_14:set_scale(v_u_10:expt_sec(p_u_14:get_scale(), 1, 0.5, p37))
            end;
        end;
        v18.anim_trigger_selected = function(_) --[[ Name: anim_trigger_selected ]] --[[ Line: 111 ]]
            --[[ Upvalues: (copy 1): p_u_14 ]]
            p_u_14:set_scale(1.25)
        end;
        return v18;
    end
}
v12.new = function(_, p_u_39, p_u_40, p_u_41, p_u_42) --[[ Name: new ]] --[[ Line: 118 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_2, (copy 3): v_u_8, (copy 4): v_u_38, (copy 5): v_u_5, (copy 6): v_u_11, (copy 7): v_u_6, (copy 8): v_u_7, (copy 9): v_u_1 ]]
    local v43 = v_u_4:SPUIObjectBase()
    local v_u_44 = 1
    local v_u_45 = 1
    local v_u_46 = v_u_2:new()
    v43.cons = function(p47) --[[ Name: cons ]] --[[ Line: 126 ]]
        --[[ Upvalues: (copy 1): p_u_42 ]]
        p47._native_size = p_u_42.PrimaryPart.Size
        p47._size = p47._native_size
        p47:create_ui_elements()
        p47:refresh_ui_elements()
    end;
    v43.refresh_ui = function(p48) --[[ Name: refresh_ui ]] --[[ Line: 134 ]]
        p48:refresh_ui_elements()
    end;
    v43.refresh_ui_elements = function(_) --[[ Name: refresh_ui_elements ]] --[[ Line: 138 ]]
        --[[ Upvalues: (copy 1): v_u_46 ]]
        for _, v49 in v_u_46:key_itr() do
            v49:refresh_from_playerblob()
        end;
    end;
    v43.create_ui_elements = function(p50) --[[ Name: create_ui_elements ]] --[[ Line: 144 ]]
        --[[ Upvalues: (copy 1): p_u_42, (ref 2): v_u_8, (ref 3): v_u_38, (copy 4): p_u_39, (ref 5): v_u_5, (copy 6): p_u_41, (ref 7): v_u_11, (ref 8): v_u_6, (copy 9): p_u_40, (ref 10): v_u_7, (copy 11): v_u_46 ]]
        local l_GearElementProto_0 = p_u_42.GearElementProto
        l_GearElementProto_0.Parent = nil
        for _, v51 in v_u_8:slot_itr() do
            local l_Anchors_0 = p_u_42.Anchors[v_u_8:slot_to_name(v51)]
            local v52 = l_GearElementProto_0:Clone()
            local v_u_53 = v_u_38:new(p_u_39, v_u_5:new(p50, p_u_42.PrimaryPart, v52), p_u_41, v51, v_u_11:new(v52):set_stat_icon_left_margin(1))
            local v54 = p_u_41:add_cycle_element(p_u_39, 1, v_u_6:new(v_u_5:new(v_u_53:get_uichild(), v_u_53:get_uichild():get_child_part(), v52.RemoveButton), p_u_40, function() --[[ Line: 165 ]]
                --[[ Upvalues: (ref 1): p_u_39, (ref 2): v_u_7, (copy 3): v_u_53 ]]
                p_u_39._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                v_u_53:remove_action()
            end))
            local v55 = p_u_41:add_cycle_element(p_u_39, 1, v_u_6:new(v_u_5:new(v_u_53:get_uichild(), v_u_53:get_uichild():get_child_part(), v52.VisibleButton), p_u_40, function() --[[ Line: 174 ]]
                --[[ Upvalues: (ref 1): p_u_39, (ref 2): v_u_7, (copy 3): v_u_53 ]]
                p_u_39._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                v_u_53:toggle_visible()
            end))
            v_u_53:add_child_uibutton(v54)
            v_u_53:set_visible_button(v55)
            v_u_53:get_uichild():set_position(l_Anchors_0.Position)
            v52.Parent = p_u_42
            v_u_46:add(v51, v_u_53)
        end;
    end;
    v43.layout = function(p56) --[[ Name: layout ]] --[[ Line: 189 ]]
        --[[ Upvalues: (copy 1): p_u_40, (ref 2): v_u_45, (copy 3): p_u_42, (copy 4): v_u_46 ]]
        p56:opt_rescale_to_max_nxy(p_u_40, 0.4, 0.7, v_u_45)
        local v57, v58 = p56:opt_update_cframe_params(p_u_40, {
            ["PositionNXY"] = Vector2.new(0, 0.525),
            ["OffsetXYZ"] = p56:anchored_offset(0, 0.5) + Vector3.new(p_u_40:get_size_from_nxy(0.015, 0).X),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v57 == true then
            p_u_42:SetPrimaryPartCFrame(v58)
        end;
        for _, v59 in v_u_46:key_itr() do
            v59:layout()
        end;
    end;
    v43.anim_trigger_slot_selected = function(_, p60) --[[ Name: anim_trigger_slot_selected ]] --[[ Line: 205 ]]
        --[[ Upvalues: (copy 1): v_u_46 ]]
        v_u_46:get(p60):anim_trigger_selected()
    end;
    v43.visual_update = function(_, p61, p62) --[[ Name: visual_update ]] --[[ Line: 209 ]]
        --[[ Upvalues: (copy 1): v_u_46 ]]
        for _, v63 in v_u_46:key_itr() do
            v63:visual_update(p61, p62)
        end;
    end;
    v43.set_alpha = function(_, p64) --[[ Name: set_alpha ]] --[[ Line: 215 ]]
        --[[ Upvalues: (ref 1): v_u_44, (ref 2): v_u_1, (copy 3): p_u_42 ]]
        if v_u_44 ~= p64 then
            v_u_44 = p64
            v_u_1:r_set_alpha(p_u_42, v_u_44)
        end;
    end;
    v43.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 224 ]]
        --[[ Upvalues: (ref 1): v_u_44 ]]
        return v_u_44;
    end;
    v43.set_scale = function(_, p65) --[[ Name: set_scale ]] --[[ Line: 225 ]]
        --[[ Upvalues: (ref 1): v_u_45 ]]
        v_u_45 = p65
    end;
    v43.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 226 ]]
        --[[ Upvalues: (ref 1): v_u_45 ]]
        return v_u_45;
    end;
    v43.get_native_size = function(p66) --[[ Name: get_native_size ]] --[[ Line: 228 ]]
        return p66._native_size;
    end;
    v43.get_size = function(p67) --[[ Name: get_size ]] --[[ Line: 231 ]]
        return p67._size;
    end;
    v43.set_size = function(p68, p69) --[[ Name: set_size ]] --[[ Line: 234 ]]
        --[[ Upvalues: (copy 1): p_u_42 ]]
        p68._size = p69
        p_u_42.PrimaryPart.Size = Vector3.new(p69.X, p69.Y, 0)
    end;
    v43.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 238 ]]
        --[[ Upvalues: (copy 1): p_u_42 ]]
        return p_u_42.PrimaryPart.Position;
    end;
    v43.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 241 ]]
        --[[ Upvalues: (copy 1): p_u_42 ]]
        return p_u_42.PrimaryPart.SurfaceGui;
    end;
    v43:cons()
    return v43;
end;
return v12;
