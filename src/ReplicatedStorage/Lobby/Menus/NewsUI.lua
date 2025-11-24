-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:40 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_6 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_8 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_9 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v10 = {}
local v_u_11 = {
    {
        ["ImageAssetId"] = v_u_1:transparent_assetid(),
        ["HeadText"] = "Loading..."
    }
}
local v_u_12 = v_u_2:new()
local v_u_13 = false
v10.get_cached_news_data = function(_, p14) --[[ Name: get_cached_news_data ]] --[[ Line: 23 ]]
    --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_11, (copy 3): v_u_12 ]]
    if v_u_13 then
        p14(v_u_11)
    else
        v_u_12:push_back(p14)
    end;
end;
v10.new = function(_, p_u_15, p_u_16, p_u_17, p_u_18) --[[ Name: new ]] --[[ Line: 31 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_1, (copy 4): v_u_9, (copy 5): v_u_5, (copy 6): v_u_4, (copy 7): v_u_7, (ref 8): v_u_11, (copy 9): v_u_8, (ref 10): v_u_13, (copy 11): v_u_12, (copy 12): v_u_6 ]]
    local v_u_19 = v_u_3:new(p_u_16, p_u_17)
    local v_u_20 = nil
    local v_u_21 = 1
    local v_u_22 = 1
    local v_u_23 = v_u_2:new()
    local v_u_24 = false
    local v_u_25 = nil
    local v_u_26 = nil
    local v_u_27 = nil
    local function f_cons() --[[ Name: cons ]] --[[ Line: 47 ]]
        --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_1, (ref 3): v_u_9, (copy 4): v_u_19, (ref 5): v_u_25, (ref 6): v_u_26, (ref 7): v_u_27, (copy 8): p_u_15, (ref 9): v_u_5, (ref 10): v_u_4, (copy 11): p_u_16, (ref 12): v_u_24, (ref 13): v_u_7, (copy 14): p_u_17, (copy 15): p_u_18, (copy 16): v_u_23, (ref 17): v_u_11, (ref 18): v_u_8, (ref 19): v_u_13, (ref 20): v_u_12, (ref 21): v_u_6 ]]
        v_u_20 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.NewsUI:Clone()
        v_u_20.Name = v_u_1:gen_name(v_u_20.Name)
        v_u_20.Parent = v_u_9:get_world_ui_folder()
        v_u_19._native_size = v_u_20.PrimaryPart.Size
        v_u_19._size = v_u_19._native_size
        local l_Frame_0 = v_u_20.MainSurface.SurfaceGui.Frame.NewsArea.Frame
        v_u_25 = l_Frame_0.NewsHead
        v_u_26 = l_Frame_0.NewsSub
        v_u_27 = l_Frame_0.NewsImage
        v_u_27.Name = v_u_1:r_set_alpha_generate_name({
            ["BackgroundAlpha"] = 0
        }, "NewsImage")
        v_u_19:add_cycle_element(p_u_15, 1, v_u_5:new(v_u_4:new(v_u_19, v_u_20.PrimaryPart, v_u_20.OkayButtonSurface), p_u_16, function() --[[ Line: 64 ]]
            --[[ Upvalues: (ref 1): v_u_24, (ref 2): p_u_15, (ref 3): v_u_7, (ref 4): p_u_17, (ref 5): v_u_19, (ref 6): p_u_18 ]]
            v_u_24 = true
            p_u_15._sfx_manager:play_sfx(v_u_7.SFX_MENU_OPEN_LONG)
            p_u_17:remove_menu(v_u_19)
            p_u_18()
        end)):set_passive_anim()
        v_u_23:push_back(v_u_19:add_cycle_element(p_u_15, 1, v_u_5:new(v_u_4:new(v_u_19, v_u_20.PrimaryPart, v_u_20.NewsItemButton1), p_u_16, function() --[[ Line: 75 ]]
            --[[ Upvalues: (ref 1): p_u_15, (ref 2): v_u_7, (ref 3): v_u_19 ]]
            p_u_15._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            v_u_19:news_item_button_pressed(1)
        end)):set_auto_zoffset_behaviour(true))
        v_u_23:push_back(v_u_19:add_cycle_element(p_u_15, 1, v_u_5:new(v_u_4:new(v_u_19, v_u_20.PrimaryPart, v_u_20.NewsItemButton2), p_u_16, function() --[[ Line: 84 ]]
            --[[ Upvalues: (ref 1): p_u_15, (ref 2): v_u_7, (ref 3): v_u_19 ]]
            p_u_15._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            v_u_19:news_item_button_pressed(2)
        end)):set_auto_zoffset_behaviour(true))
        v_u_23:push_back(v_u_19:add_cycle_element(p_u_15, 1, v_u_5:new(v_u_4:new(v_u_19, v_u_20.PrimaryPart, v_u_20.NewsItemButton3), p_u_16, function() --[[ Line: 93 ]]
            --[[ Upvalues: (ref 1): p_u_15, (ref 2): v_u_7, (ref 3): v_u_19 ]]
            p_u_15._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            v_u_19:news_item_button_pressed(3)
        end)):set_auto_zoffset_behaviour(true))
        v_u_19:load_news_data(v_u_11)
        p_u_15._evt:wait_on_event_once(v_u_8.EVT_News_ServerRequestNewsDataResponse, function(p_u_28) --[[ Line: 100 ]]
            --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_13, (ref 3): v_u_12, (ref 4): v_u_6, (ref 5): v_u_19 ]]
            v_u_11 = p_u_28
            v_u_13 = true
            for _, v_u_29 in v_u_12:key_itr() do
                local v30, v31 = pcall(function() --[[ Line: 105 ]]
                    --[[ Upvalues: (copy 1): v_u_29, (copy 2): p_u_28 ]]
                    v_u_29(p_u_28)
                end)
                if not v30 then
                    v_u_6:warnf("NewsUI:load_news_data:fn:err: %s", v31)
                end;
            end;
            v_u_12:clear()
            v_u_19:load_news_data(v_u_11)
        end)
        p_u_15._evt:fire_event_to_server(v_u_8.EVT_News_ClientRequestNewsData)
        v_u_19:reset_selected_item()
        v_u_19:transition_update_visual(0)
        v_u_19:layout()
    end;
    local v_u_32 = -1
    v_u_19.load_news_data = function(p33, p34) --[[ Name: load_news_data ]] --[[ Line: 124 ]]
        --[[ Upvalues: (ref 1): v_u_24, (copy 2): v_u_23, (ref 3): v_u_32 ]]
        if v_u_24 ~= true then
            for v35 = 1, 3 do
                local v_u_36 = p34[v35]
                local v_u_37 = v_u_23:get(v35)
                if p34 and (p34[v35] and #p34 > 0) then
                    pcall(function() --[[ Line: 131 ]]
                        --[[ Upvalues: (copy 1): v_u_37, (copy 2): v_u_36 ]]
                        v_u_37:get_part().SurfaceGui.Frame.TextLabel.Text = v_u_36.HeadText
                    end)
                    v_u_37:set_visible(true)
                else
                    v_u_37:set_visible(false)
                end;
            end;
            v_u_32 = -1
            p33:news_item_button_pressed(1)
        end;
    end;
    v_u_19.news_item_button_pressed = function(_, p38) --[[ Name: news_item_button_pressed ]] --[[ Line: 143 ]]
        --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_32, (ref 3): v_u_25, (ref 4): v_u_26, (ref 5): v_u_27, (copy 6): v_u_23, (ref 7): v_u_1 ]]
        if #v_u_11 < p38 then
            return;
        elseif p38 ~= v_u_32 then
            v_u_32 = p38
            local v39 = v_u_11[v_u_32]
            if v39.HeadText == nil then
                v_u_25.Text = ""
            else
                v_u_25.Text = v39.HeadText
            end;
            if v39.SubText == nil then
                v_u_26.Text = ""
            else
                v_u_26.Text = v39.SubText
            end;
            if v39.ImageAssetId == nil then
                v_u_27.Image = ""
            else
                v_u_27.Image = v39.ImageAssetId
            end;
            for v40 = 1, 3 do
                local v41 = v_u_23:get(v40)
                if v40 == p38 then
                    v41:get_part().SurfaceGui.Frame.ImageLabel.Image = v_u_1:get_news_pageitem_selected_assetid()
                else
                    v41:get_part().SurfaceGui.Frame.ImageLabel.Image = v_u_1:get_news_pageitem_unselected_assetid()
                end;
            end;
        end;
    end;
    v_u_19.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 175 ]]
        --[[ Upvalues: (ref 1): v_u_20 ]]
        v_u_20:Destroy()
    end;
    v_u_19.layout = function(p42) --[[ Name: layout ]] --[[ Line: 179 ]]
        --[[ Upvalues: (copy 1): p_u_16, (ref 2): v_u_22, (ref 3): v_u_20 ]]
        p42:opt_rescale_to_max_nxy(p_u_16, 0.8, 0.8, v_u_22)
        local v43, v44 = p42:opt_update_cframe_params(p_u_16, {
            ["PositionNXY"] = Vector2.new(0.5, 0.5),
            ["OffsetXYZ"] = p42:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v43 == true then
            v_u_20:SetPrimaryPartCFrame(v44)
        end;
    end;
    v_u_19.set_alpha = function(_, p45) --[[ Name: set_alpha ]] --[[ Line: 191 ]]
        --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_1, (ref 3): v_u_20 ]]
        if v_u_21 ~= p45 then
            v_u_21 = p45
            v_u_1:r_set_alpha(v_u_20, v_u_21)
        end;
    end;
    v_u_19.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 197 ]]
        --[[ Upvalues: (ref 1): v_u_21 ]]
        return v_u_21;
    end;
    v_u_19.set_scale = function(_, p46) --[[ Name: set_scale ]] --[[ Line: 198 ]]
        --[[ Upvalues: (ref 1): v_u_22 ]]
        v_u_22 = p46
    end;
    v_u_19.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 199 ]]
        --[[ Upvalues: (ref 1): v_u_22 ]]
        return v_u_22;
    end;
    v_u_19.get_native_size = function(p47) --[[ Name: get_native_size ]] --[[ Line: 201 ]]
        return p47._native_size;
    end;
    v_u_19.get_size = function(p48) --[[ Name: get_size ]] --[[ Line: 204 ]]
        return p48._size;
    end;
    v_u_19.set_size = function(p49, p50) --[[ Name: set_size ]] --[[ Line: 207 ]]
        --[[ Upvalues: (ref 1): v_u_20 ]]
        p49._size = p50
        v_u_20.PrimaryPart.Size = Vector3.new(p50.X, p50.Y, 0)
    end;
    v_u_19.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 211 ]]
        --[[ Upvalues: (ref 1): v_u_20 ]]
        return v_u_20.PrimaryPart.Position;
    end;
    v_u_19.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 214 ]]
        --[[ Upvalues: (ref 1): v_u_20 ]]
        return v_u_20.PrimaryPart.SurfaceGui;
    end;
    f_cons()
    return v_u_19;
end;
return v10;
