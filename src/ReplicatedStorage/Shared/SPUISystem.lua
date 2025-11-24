-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:03 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPVector)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPRect)
local v_u_4 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_5 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.Shared.LVector3)
local v_u_7 = require(game.ReplicatedStorage.Shared.LCFrame)
local v_u_8 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_121 = {
    ["cframe_params_default"] = function(_) --[[ Name: cframe_params_default ]] --[[ Line: 13 ]]
        --[[ Upvalues: (copy 1): v_u_6 ]]
        return {
            ["PositionNXY"] = v_u_6.new(),
            ["OffsetXYZ"] = v_u_6.new(),
            ["LocalRotationOffset"] = v_u_6.new()
        };
    end,
    ["new"] = function(_, p_u_9) --[[ Name: new ]] --[[ Line: 170 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_6, (copy 3): v_u_7 ]]
        local v_u_33 = {
            ["_normal_dir"] = Vector3.new(),
            ["_screen_tl_pos"] = Vector3.new(),
            ["_screen_tr_pos"] = Vector3.new(),
            ["_screen_bl_pos"] = Vector3.new(),
            ["_screen_br_pos"] = Vector3.new(),
            ["get_normal_dir"] = function(p10) --[[ Name: get_normal_dir ]] --[[ Line: 271 ]]
                return p10._normal_dir;
            end,
            ["get_up_dir"] = function(p11) --[[ Name: get_up_dir ]] --[[ Line: 282 ]]
                return (p11._screen_br_pos - p11._screen_tr_pos).Unit * -1;
            end,
            ["get_cframe_param_comparator"] = function(_, p12, p13) --[[ Name: get_cframe_param_comparator ]] --[[ Line: 427 ]]
                local v14
                if p12.PositionNXY == p13.PositionNXY and p12.OffsetXYZ == p13.OffsetXYZ then
                    v14 = p12.LocalRotationOffset == p13.LocalRotationOffset
                else
                    v14 = false
                end;
                return v14;
            end,
            ["uiobj_rescale_to_max_nxy"] = function(p15, p16, p17, p18, p19) --[[ Name: uiobj_rescale_to_max_nxy ]] --[[ Line: 451 ]]
                local v20 = p19 == nil and 1 or p19
                local v21 = p16:get_native_size()
                local v22 = p15:get_size_from_nxy(1, 1)
                local v23 = v21.X / (v22.X * p17)
                local v24 = v21.Y / (v22.Y * p18)
                if v23 < 1 and v24 < 1 then
                    p16:set_size(p16:get_native_size() * v20)
                else
                    p16:set_size(p16:get_native_size() * (1 / math.max(v23, v24)) * v20)
                end;
            end,
            ["get_xy_basis"] = function(p25) --[[ Name: get_xy_basis ]] --[[ Line: 469 ]]
                local l_Unit_0 = p25:get_up_dir():Cross(p25:get_normal_dir()).Unit
                return l_Unit_0, p25:get_normal_dir():Cross(l_Unit_0).Unit;
            end,
            ["uiobj_get_size_nxy"] = function(p26, p27) --[[ Name: uiobj_get_size_nxy ]] --[[ Line: 477 ]]
                local v28 = p27:get_size()
                return p26:get_size_nxy_from_uiplane_xy(v28.X, v28.Y);
            end,
            ["get_size_nxy_from_uiplane_xy"] = function(p29, p30, p31) --[[ Name: get_size_nxy_from_uiplane_xy ]] --[[ Line: 482 ]]
                local v32 = p29:get_size_from_nxy(1, 1)
                return Vector2.new(p30 / v32.X, p31 / v32.Y);
            end
        }
        local v_u_34 = true
        local v_u_35 = CFrame.new()
        local v_u_36 = Vector3.new(-1, -1, -1)
        local v_u_37 = false
        v_u_33.is_layout_updated = function(_) --[[ Name: is_layout_updated ]] --[[ Line: 184 ]]
            --[[ Upvalues: (ref 1): v_u_37 ]]
            return v_u_37;
        end;
        local v_u_38 = false
        v_u_33.force_layout_updated = function(_) --[[ Name: force_layout_updated ]] --[[ Line: 188 ]]
            --[[ Upvalues: (ref 1): v_u_38 ]]
            v_u_38 = true
        end;
        local v_u_39 = true
        v_u_33.set_distance_to_camera = function(p40, p41) --[[ Name: set_distance_to_camera ]] --[[ Line: 193 ]]
            --[[ Upvalues: (ref 1): v_u_39, (ref 2): p_u_9 ]]
            v_u_39 = true
            p_u_9 = p41
            return p40;
        end;
        v_u_33.calculate_center_position_and_normal_for_distance = function(_, p42) --[[ Name: calculate_center_position_and_normal_for_distance ]] --[[ Line: 199 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v43 = v_u_1:get_camera_cframe()
            local l_Unit_1 = v43.LookVector.Unit
            return v43.p + l_Unit_1 * p42, l_Unit_1 * -1;
        end;
        local v_u_44 = Vector3.new()
        local function _() --[[ Name: recalculate_center_position_and_normal ]] --[[ Line: 209 ]]
            --[[ Upvalues: (copy 1): v_u_33, (ref 2): p_u_9, (ref 3): v_u_44 ]]
            local v45, v46 = v_u_33:calculate_center_position_and_normal_for_distance(p_u_9)
            v_u_33._normal_dir = v46
            v_u_44 = v45
        end;
        v_u_33.calculate_nxy_position = function(p47, p48, p49, p50) --[[ Name: calculate_nxy_position ]] --[[ Line: 215 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_44 ]]
            local v51, v52 = v_u_1:nxy_to_nontopbar_screen_pos(p48, p49)
            local v53 = v_u_1:get_camera():ScreenPointToRay(v51, v52)
            if p50 == nil then
                p50 = v_u_44
            end;
            local v54, v55 = v_u_1:plane_intersect(v53.Origin, v53.Direction.Unit, p50, p47._normal_dir)
            if v54 then
                return v55;
            else
                return p50;
            end;
        end;
        v_u_33.layout = function(p56) --[[ Name: layout ]] --[[ Line: 237 ]]
            --[[ Upvalues: (ref 1): v_u_39, (ref 2): v_u_1, (ref 3): v_u_35, (ref 4): v_u_36, (ref 5): v_u_38, (ref 6): v_u_37, (copy 7): v_u_33, (ref 8): p_u_9, (ref 9): v_u_44, (ref 10): v_u_34 ]]
            if v_u_39 == true then
                v_u_39 = false
            elseif v_u_1:get_camera_cframe() == v_u_35 and (v_u_36 == v_u_1:screen_size() and v_u_38 == false) then
                v_u_37 = false
                return;
            end;
            v_u_38 = false
            v_u_36 = v_u_1:screen_size()
            v_u_35 = v_u_1:get_camera_cframe()
            v_u_37 = true
            local v57, v58 = v_u_33:calculate_center_position_and_normal_for_distance(p_u_9)
            v_u_33._normal_dir = v58
            v_u_44 = v57
            if v_u_1:is_console_ui() then
                local v59 = v_u_1:topbar_size() / v_u_1:screen_size().Y
                p56._screen_tl_pos = p56:calculate_nxy_position(0, v59)
                p56._screen_tr_pos = p56:calculate_nxy_position(1, v59)
                p56._screen_bl_pos = p56:calculate_nxy_position(0, 1)
                p56._screen_br_pos = p56:calculate_nxy_position(1, 1)
            else
                p56._screen_tl_pos = p56:calculate_nxy_position(0, 0)
                p56._screen_tr_pos = p56:calculate_nxy_position(1, 0)
                p56._screen_bl_pos = p56:calculate_nxy_position(0, 1)
                p56._screen_br_pos = p56:calculate_nxy_position(1, 1)
            end;
            v_u_34 = true
        end;
        local v_u_60 = v_u_6.new()
        v_u_33.get_normal_dir_lv = function(p61) --[[ Name: get_normal_dir_lv ]] --[[ Line: 276 ]]
            --[[ Upvalues: (copy 1): v_u_60 ]]
            local l__normal_dir_0 = p61._normal_dir
            v_u_60:set(l__normal_dir_0.X, l__normal_dir_0.Y, l__normal_dir_0.Z)
            return v_u_60;
        end;
        local v_u_62 = Vector2.new()
        local v_u_63 = Vector2.new()
        local v_u_64 = Vector2.new()
        v_u_33.get_pos_from_nxy = function(p65, p66, p67) --[[ Name: get_pos_from_nxy ]] --[[ Line: 291 ]]
            --[[ Upvalues: (ref 1): v_u_34, (ref 2): v_u_62, (ref 3): v_u_63, (ref 4): v_u_64 ]]
            if v_u_34 == true then
                v_u_62 = p65._screen_tr_pos - p65._screen_tl_pos
                v_u_63 = p65._screen_br_pos - p65._screen_bl_pos
                v_u_64 = p65._screen_bl_pos - p65._screen_tl_pos
                v_u_34 = false
            end;
            return v_u_62 * p66 * (1 - p67) + v_u_63 * p66 * p67 + v_u_64 * p67 + p65._screen_tl_pos;
        end;
        v_u_33.get_nxy_from_pos = function(_, p68) --[[ Name: get_nxy_from_pos ]] --[[ Line: 318 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            return v_u_1:pos_to_nxy(p68);
        end;
        local v_u_69 = {}
        local v_u_70 = v_u_6.new(0.5, 0.5)
        local v_u_71 = v_u_6.new()
        local v_u_72 = v_u_6.new()
        local v_u_73 = v_u_6.new()
        local v_u_74 = v_u_6.new()
        local v_u_75 = v_u_6.new()
        local v_u_76 = v_u_7.new()
        local v_u_77 = v_u_7.new()
        local v_u_78 = v_u_7.new()
        local v_u_79 = v_u_7.new()
        local v_u_80 = v_u_7.new()
        local v_u_81 = v_u_7.new()
        v_u_33.get_cframe = function(p82, p83) --[[ Name: get_cframe ]] --[[ Line: 340 ]]
            --[[ Upvalues: (copy 1): v_u_69, (copy 2): v_u_70, (copy 3): v_u_71, (copy 4): v_u_72, (copy 5): v_u_73, (copy 6): v_u_74, (copy 7): v_u_75, (copy 8): v_u_76, (copy 9): v_u_77, (copy 10): v_u_78, (copy 11): v_u_79, (copy 12): v_u_80, (copy 13): v_u_81, (ref 14): v_u_1 ]]
            if p83 == nil then
                p83 = v_u_69
            end;
            if p83.PositionNXY == nil then
                p83.PositionNXY = v_u_70
                p83.PositionNXY:set(0.5, 0.5)
            end;
            if p83.OffsetXYZ == nil then
                p83.OffsetXYZ = v_u_71
                p83.OffsetXYZ:set()
            end;
            if p83.LocalRotationOffset == nil then
                p83.LocalRotationOffset = v_u_72
                p83.LocalRotationOffset:set()
            end;
            local v84 = v_u_73
            local v85 = v_u_74
            local v86 = v_u_75
            local v87 = v_u_76
            local v88 = v_u_77
            local v89 = v_u_78
            local v90 = v_u_79
            local v91 = v_u_80
            local v92 = v_u_81
            v84:set(-p83.OffsetXYZ.X, p83.OffsetXYZ.Y, p83.OffsetXYZ.Z)
            local v93 = p82:get_pos_from_nxy(p83.PositionNXY.X, p83.PositionNXY.Y)
            v86:from_vector3(p82._normal_dir)
            v86:scale(-0.025)
            v85:store_add_result(v93, v86)
            v87:from_cframe(v_u_1:get_camera_cframe_lv())
            v87.p:from_vector3(v85)
            v_u_1:angles_lv(v88, 180, 0, 180)
            v89:store_mul_result(v87, v88)
            v90:set_identity()
            v90.p:set(v84.X, v84.Y, v84.Z)
            v_u_1:angles_lv(v91, p83.LocalRotationOffset.X, p83.LocalRotationOffset.Y, p83.LocalRotationOffset.Z)
            v92:store_mul_result(v89, v90)
            v92:store_mul_result(v92, v91)
            return v92:to_cframe();
        end;
        local v_u_94 = 0
        local v_u_95 = 0
        v_u_33.get_size_from_nxy = function(p96, p97, p98) --[[ Name: get_size_from_nxy ]] --[[ Line: 436 ]]
            --[[ Upvalues: (ref 1): v_u_34, (ref 2): v_u_94, (ref 3): v_u_95 ]]
            if v_u_34 == true then
                v_u_94 = (p96:get_pos_from_nxy(1, 1) - p96:get_pos_from_nxy(0, 1)).Magnitude
                v_u_95 = (p96:get_pos_from_nxy(1, 1) - p96:get_pos_from_nxy(1, 0)).Magnitude
            end;
            return Vector2.new(v_u_94 * p97, v_u_95 * p98);
        end;
        v_u_33.get_cursor_nxy = function(_) --[[ Name: get_cursor_nxy ]] --[[ Line: 490 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            return v_u_1:get_cursor_nxy();
        end;
        v_u_33.set_focus_plane_from_position = function(p99, p100) --[[ Name: set_focus_plane_from_position ]] --[[ Line: 494 ]]
            --[[ Upvalues: (copy 1): v_u_33, (ref 2): p_u_9, (ref 3): v_u_44, (ref 4): v_u_1 ]]
            local v101, v102 = v_u_33:calculate_center_position_and_normal_for_distance(p_u_9)
            v_u_33._normal_dir = v102
            v_u_44 = v101
            p99:set_distance_to_camera((p100 - v_u_1:get_camera_cframe().p):Dot((p99:get_normal_dir() * -1).Unit))
        end;
        v_u_33:layout()
        return v_u_33;
    end,
    ["part_get_front_xy_basis"] = function(_, p103) --[[ Name: part_get_front_xy_basis ]] --[[ Line: 505 ]]
        return p103.CFrame.rightVector * -1, p103.CFrame.upVector;
    end,
    ["CursorFramePositionCalc"] = {
        ["new"] = function(_, p_u_104, p_u_105, p_u_106, p_u_107) --[[ Name: new ]] --[[ Line: 511 ]]
            --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_3, (copy 3): v_u_1 ]]
            local v108 = {}
            local v_u_109 = v_u_2:new(0, 0, 0)
            local v_u_110 = v_u_3:new()
            local v_u_111 = v_u_3:new()
            local v_u_112 = v_u_3:new()
            local v_u_113 = v_u_2:new(0, 0, 0)
            v108.test_cursor_over_frame = function(_) --[[ Name: test_cursor_over_frame ]] --[[ Line: 525 ]]
                --[[ Upvalues: (copy 1): p_u_104, (copy 2): p_u_105, (copy 3): v_u_109, (ref 4): v_u_1, (copy 5): v_u_110, (copy 6): p_u_106, (copy 7): v_u_111, (copy 8): p_u_107, (copy 9): v_u_112, (copy 10): v_u_113 ]]
                local v114 = false
                local v115 = p_u_104:get_cursor_nxy()
                local v116 = p_u_105:get_nrect(p_u_104)
                if v116:contains_vec2(v115) then
                    local v117 = v_u_109:set(v_u_1:clamp((v115.X - v116._x1) / (v116._x2 - v116._x1), 0, 1), v_u_1:clamp((v115.Y - v116._y1) / (v116._y2 - v116._y1), 0, 1))
                    local v118 = v_u_110:set(0, 0, p_u_106.CanvasSize.X, p_u_106.CanvasSize.Y)
                    local v119 = v_u_111:set(p_u_107.AbsolutePosition.X, p_u_107.AbsolutePosition.Y, p_u_107.AbsolutePosition.X + p_u_107.AbsoluteSize.X, p_u_107.AbsolutePosition.Y + p_u_107.AbsoluteSize.Y)
                    local v120 = v_u_112:set(v119._x1 / (v118._x2 - v118._x1), v119._y1 / (v118._y2 - v118._y1), v119._x2 / (v118._x2 - v118._x1), v119._y2 / (v118._y2 - v118._y1))
                    if v120:contains_vec2(v117:to_vector2()) then
                        v_u_113:set((v117._x - v120._x1) / (v120._x2 - v120._x1) * (v119._x2 - v119._x1), (v117._y - v120._y1) / (v120._y2 - v120._y1) * (v119._y2 - v119._y1))
                        v114 = true
                    end;
                end;
                return v114, v_u_113;
            end;
            return v108;
        end
    }
}
v_u_121.SPUIObjectBase = function(_) --[[ Name: SPUIObjectBase ]] --[[ Line: 21 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_8, (copy 3): v_u_6, (copy 4): v_u_3, (copy 5): v_u_2, (copy 6): v_u_4, (copy 7): v_u_121 ]]
    local v127 = {
        ["anchored_offset"] = function(p122, p123, p124) --[[ Name: anchored_offset ]] --[[ Line: 50 ]]
            return p122:anchored_offset_from_size(p123, p124, p122:get_size());
        end,
        ["opt_update_cframe_params"] = function(_, p125, p126) --[[ Name: opt_update_cframe_params ]] --[[ Line: 123 ]]
            return true, p125:get_cframe(p126);
        end
    }
    v127.get_native_size = function(_) --[[ Name: get_native_size ]] --[[ Line: 24 ]]
        --[[ Upvalues: (ref 1): v_u_5 ]]
        v_u_5:errf("NOIMPL")
        return Vector2.new();
    end;
    v127.get_size = function(_) --[[ Name: get_size ]] --[[ Line: 25 ]]
        --[[ Upvalues: (ref 1): v_u_5 ]]
        v_u_5:errf("NOIMPL")
        return Vector2.new();
    end;
    v127.set_size = function(_, _) --[[ Name: set_size ]] --[[ Line: 26 ]]
        --[[ Upvalues: (ref 1): v_u_5 ]]
        v_u_5:errf("NOIMPL")
    end;
    v127.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 27 ]]
        --[[ Upvalues: (ref 1): v_u_5 ]]
        v_u_5:errf("NOIMPL")
        return Vector3.new();
    end;
    v127.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 28 ]]
        --[[ Upvalues: (ref 1): v_u_5 ]]
        v_u_5:errf("NOIMPL")
        return nil;
    end;
    local v_u_128 = 1
    v127.get_alloc_child_id = function(_) --[[ Name: get_alloc_child_id ]] --[[ Line: 31 ]]
        --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_128 ]]
        if v_u_8.DoZOffsetChildren ~= true then
            return 0;
        end;
        local v129 = v_u_128
        v_u_128 = v_u_128 + 1
        return v129;
    end;
    local v_u_130 = v_u_6:new()
    v127.anchored_offset_from_size = function(_, p131, p132, p133) --[[ Name: anchored_offset_from_size ]] --[[ Line: 42 ]]
        --[[ Upvalues: (copy 1): v_u_130 ]]
        return v_u_130:set(-(p131 - 0.5) * p133.X, (p132 - 0.5) * p133.Y, 0);
    end;
    local v_u_134 = v_u_3:new(0, 0, 0, 0)
    v127.get_nrect = function(p135, p136) --[[ Name: get_nrect ]] --[[ Line: 55 ]]
        --[[ Upvalues: (copy 1): v_u_134 ]]
        local v137 = p136:get_nxy_from_pos(p135:get_pos())
        local v138 = p136:uiobj_get_size_nxy(p135)
        v_u_134:set_centerxy_wid_hei(v137.X, v137.Y, v138.X, v138.Y)
        return v_u_134;
    end;
    local v_u_139 = v_u_2:new()
    local v_u_140 = v_u_2:new()
    v127.uichild_get_nbounds = function(p141, p142, p143) --[[ Name: uichild_get_nbounds ]] --[[ Line: 72 ]]
        --[[ Upvalues: (copy 1): v_u_139, (copy 2): v_u_140, (ref 3): v_u_4 ]]
        local v144 = p141:get_sgui()
        local l_CanvasSize_0 = v144.CanvasSize
        local l_AbsoluteSize_0 = p143.Parent.AbsoluteSize
        v_u_139:set(0, 0)
        v_u_140:set(p143.Size.X.Offset + p143.Size.X.Scale * l_AbsoluteSize_0.X, p143.Size.Y.Offset + p143.Size.Y.Scale * l_AbsoluteSize_0.Y)
        v_u_139._x = v_u_139._x - p143.AnchorPoint.X * p143.AbsoluteSize.X
        v_u_139._y = v_u_139._y - p143.AnchorPoint.Y * p143.AbsoluteSize.Y
        while p143 ~= v144 and p143 ~= nil do
            v_u_139._x = v_u_139._x + p143.Position.X.Offset
            v_u_139._y = v_u_139._y + p143.Position.Y.Offset
            local l_Parent_0 = p143.Parent
            local l_AbsoluteSize_1 = l_Parent_0.AbsoluteSize
            v_u_139._x = v_u_139._x + l_AbsoluteSize_1.X * p143.Position.X.Scale
            v_u_139._y = v_u_139._y + l_AbsoluteSize_1.Y * p143.Position.Y.Scale
            p143 = l_Parent_0
        end;
        local v145 = p141:get_nrect(p142)
        v145:set(v_u_4:Lerp(v145._x1, v145._x2, v_u_139._x / l_CanvasSize_0.X), v_u_4:Lerp(v145._y1, v145._y2, v_u_139._y / l_CanvasSize_0.Y), v_u_4:Lerp(v145._x1, v145._x2, (v_u_139._x + v_u_140._x) / l_CanvasSize_0.X), v_u_4:Lerp(v145._y1, v145._y2, (v_u_139._y + v_u_140._y) / l_CanvasSize_0.Y))
        return v145;
    end;
    local v_u_146 = v_u_121:cframe_params_default()
    v_u_6:new(-1, -1, -1)
    v127.update_last_cframe_params = function(_, p147) --[[ Name: update_last_cframe_params ]] --[[ Line: 117 ]]
        --[[ Upvalues: (copy 1): v_u_146 ]]
        v_u_146.PositionNXY:from_vector3(p147.PositionNXY)
        v_u_146.OffsetXYZ:from_vector3(p147.OffsetXYZ)
        v_u_146.LocalRotationOffset:from_vector3(p147.LocalRotationOffset)
    end;
    local v_u_148 = -1
    local v_u_149 = -1
    local v_u_150 = -1
    v127.opt_rescale_to_max_nxy = function(p151, p152, p153, p154, p155) --[[ Name: opt_rescale_to_max_nxy ]] --[[ Line: 155 ]]
        --[[ Upvalues: (ref 1): v_u_148, (ref 2): v_u_149, (ref 3): v_u_150 ]]
        local v156 = p155 == nil and 1 or p155
        if v_u_148 ~= p153 or (v_u_149 ~= p154 or (v156 ~= v_u_150 or p152:is_layout_updated())) then
            p152:uiobj_rescale_to_max_nxy(p151, p153, p154, v156)
            v_u_150 = v156
            v_u_148 = p153
            v_u_149 = p154
        end;
    end;
    return v127;
end;
return v_u_121;
